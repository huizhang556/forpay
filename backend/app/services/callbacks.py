import hashlib
import hmac
import logging
import time
from datetime import UTC, datetime, timedelta

import httpx
from app.models import CallbackAttempt, MerchantApiKey, Order, OrderStatus, PaymentEvent
from app.services.orders import _validate_callback_url
from app.services.security import _fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def queue_callback(db: Session, order: Order) -> CallbackAttempt | None:
    if not order.notify_url:
        return None
    attempt = CallbackAttempt(
        order_id=order.id,
        callback_url=order.notify_url,
        request_body={"out_trade_no": order.out_trade_no, "trade_status": "TRADE_SUCCESS", "money": str(order.amount)},
    )
    order.status = OrderStatus.CALLBACK_PENDING
    db.add(attempt)
    db.add(PaymentEvent(order_id=order.id, event_type="callback.queued", payload={}))
    db.commit()
    return attempt


async def deliver_callback(db: Session, attempt: CallbackAttempt) -> bool:
    try:
        _validate_callback_url(attempt.callback_url)
        body = "&".join(f"{key}={value}" for key, value in sorted(attempt.request_body.items())).encode()
        order = db.get(Order, attempt.order_id)
        headers = {}
        if order:
            merchant_key = db.scalar(select(MerchantApiKey).where(MerchantApiKey.merchant_id == order.merchant_id, MerchantApiKey.enabled.is_(True)))
            if merchant_key and merchant_key.secret_encrypted:
                secret = _fernet().decrypt(merchant_key.secret_encrypted.encode())
                timestamp = str(int(time.time()))
                headers = {
                    "X-ForPay-Timestamp": timestamp,
                    "X-ForPay-Signature": hmac.new(secret, timestamp.encode() + b"." + body, hashlib.sha256).hexdigest(),
                }
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            response = await client.post(attempt.callback_url, data=attempt.request_body, headers=headers)
        attempt.response_status = response.status_code
        attempt.response_body = response.text[:2000]
        attempt.attempt_count += 1
        success = 200 <= response.status_code < 300
    except httpx.HTTPError as exc:
        logger.warning("callback delivery failed", extra={"attempt_id": attempt.id, "error": str(exc)[:200]})
        attempt.response_body = str(exc)[:2000]
        attempt.attempt_count += 1
        success = False
    if success:
        attempt.status = "success"
        order = db.get(Order, attempt.order_id)
        if order:
            order.status = OrderStatus.CALLBACK_SUCCESS
    else:
        attempt.status = "failed" if attempt.attempt_count >= 8 else "pending"
        attempt.next_retry_at = datetime.now(UTC) + timedelta(minutes=min(attempt.attempt_count * 2, 30))
    db.commit()
    logger.info("callback delivery completed", extra={"attempt_id": attempt.id, "success": success, "attempt_count": attempt.attempt_count})
    return success
