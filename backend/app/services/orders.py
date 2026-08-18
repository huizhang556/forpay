import ipaddress
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

from app.core.config import get_settings
from app.models import Order, OrderStatus, PaymentChannel, PaymentEvent
from app.schemas.payment import OrderCreate
from sqlalchemy import select
from sqlalchemy.orm import Session


def _validate_callback_url(url: str | None) -> None:
    if not url:
        return
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("回调地址必须是有效的 HTTP(S) 地址")
    if get_settings().environment != "development" and parsed.scheme != "https":
        raise ValueError("生产环境回调地址必须使用 HTTPS")
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "metadata.google.internal"}:
        raise ValueError("回调地址不能指向本机或云元数据服务")
    try:
        address = ipaddress.ip_address(hostname)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise ValueError("回调地址不能指向内网或保留地址")
    except ValueError as exc:
        if str(exc).startswith("回调地址"):
            raise


def _next_display_amount(db: Session, channel_id: int, amount: Decimal) -> Decimal:
    settings = get_settings()
    step = Decimal(settings.amount_suffix_cents) / Decimal(100)
    active = db.scalars(
        select(Order.display_amount).where(
            Order.channel_id == channel_id,
            Order.status.in_([OrderStatus.CREATED, OrderStatus.WAITING_PAYMENT]),
            Order.expires_at > datetime.now(UTC),
        ).with_for_update()
    ).all()
    used = {Decimal(value) for value in active}
    for offset in range(0, 100):
        candidate = amount + (step * offset)
        if candidate not in used:
            return candidate
    raise ValueError("当前通道的金额尾数已用尽，请稍后重试或增加收款通道")


def create_order(db: Session, payload: OrderCreate, idempotency_key: str | None = None) -> Order:
    _validate_callback_url(str(payload.notify_url) if payload.notify_url else None)
    _validate_callback_url(str(payload.return_url) if payload.return_url else None)
    if idempotency_key:
        existing = db.scalar(select(Order).where(Order.merchant_id == payload.merchant_id, Order.idempotency_key == idempotency_key))
        if existing:
            return existing
    channel = db.scalar(
        select(PaymentChannel).where(
            PaymentChannel.id == payload.channel_id,
            PaymentChannel.enabled.is_(True),
        ).with_for_update()
    )
    if not channel:
        raise ValueError("收款通道不存在或已停用")
    out_trade_no = payload.out_trade_no or f"FP{datetime.now(UTC):%Y%m%d%H%M%S}{uuid4().hex[:8].upper()}"
    if db.scalar(select(Order.id).where(Order.out_trade_no == out_trade_no)):
        raise ValueError("商户订单号已存在")
    now = datetime.now(UTC)
    order = Order(
        merchant_id=payload.merchant_id,
        out_trade_no=out_trade_no,
        idempotency_key=idempotency_key,
        public_token=secrets.token_urlsafe(32),
        subject=payload.subject,
        amount=payload.amount,
        display_amount=_next_display_amount(db, channel.id, payload.amount),
        channel_id=channel.id,
        status=OrderStatus.WAITING_PAYMENT,
        notify_url=str(payload.notify_url) if payload.notify_url else None,
        return_url=str(payload.return_url) if payload.return_url else None,
        expires_at=now + timedelta(minutes=get_settings().order_ttl_minutes),
    )
    db.add(order)
    db.flush()
    db.add(PaymentEvent(order_id=order.id, event_type="order.created", payload={"display_amount": str(order.display_amount)}))
    db.commit()
    db.refresh(order)
    return order


def expire_orders(db: Session) -> int:
    now = datetime.now(UTC)
    orders = db.scalars(
        select(Order).where(
            Order.status.in_([OrderStatus.CREATED, OrderStatus.WAITING_PAYMENT]),
            Order.expires_at <= now,
        ).with_for_update()
    ).all()
    for order in orders:
        order.status = OrderStatus.EXPIRED
        db.add(PaymentEvent(order_id=order.id, event_type="order.expired", payload={}))
    db.commit()
    return len(orders)
