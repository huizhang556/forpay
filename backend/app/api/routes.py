import secrets
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    CallbackAttempt,
    Order,
    PaymentChannel,
    PaymentEvent,
    PaymentNotification,
    Product,
)
from app.schemas.payment import (
    AdminLogin,
    ApiKeyCreate,
    ApiKeyCreated,
    ChannelCreate,
    ChannelRead,
    CheckoutCreate,
    ManualMatch,
    NotificationCreate,
    NotificationResult,
    OrderCreate,
    OrderRead,
    ProductCreate,
    ProductRead,
)
from app.services.callbacks import deliver_callback, queue_callback
from app.services.notifications import handle_notification
from app.services.orders import create_order
from app.services.security import (
    admin_session_value,
    authenticate_signature,
    checkout_session_value,
    create_api_key,
)
from app.services.updates import UpdateError, check_update
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter()


def require_admin_token(
    x_forpay_admin_token: str | None = Header(default=None),
    forpay_admin: str | None = Cookie(default=None),
) -> None:
    expected = get_settings().admin_token
    valid_header = x_forpay_admin_token and expected and secrets.compare_digest(expected, x_forpay_admin_token)
    valid_cookie = forpay_admin and secrets.compare_digest(admin_session_value(), forpay_admin)
    if not expected or not (valid_header or valid_cookie):
        raise HTTPException(status_code=401, detail="管理令牌无效")


def require_monitor_token(x_forpay_monitor_token: str | None = Header(default=None)) -> None:
    expected = get_settings().monitor_token
    if not expected or not x_forpay_monitor_token or not secrets.compare_digest(expected, x_forpay_monitor_token):
        raise HTTPException(status_code=401, detail="监控端令牌无效")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forpay"}


@router.post("/products", response_model=ProductRead, status_code=201)
def add_product(payload: ProductCreate, _: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products", response_model=list[ProductRead])
def list_products(_: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    return db.scalars(select(Product).where(Product.enabled.is_(True)).order_by(Product.created_at.desc())).all()


@router.post("/checkout", response_model=OrderRead, status_code=201)
def create_checkout(payload: CheckoutCreate, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    channel = db.get(PaymentChannel, payload.channel_id)
    if not product or not product.enabled or not channel or not channel.enabled:
        raise HTTPException(status_code=404, detail="商品或收款通道不存在")
    checkout = OrderCreate(
        merchant_id=product.merchant_id,
        subject=product.name,
        amount=product.price,
        channel_id=channel.id,
    )
    try:
        order = create_order(db, checkout, "checkout-" + secrets.token_urlsafe(18))
        order.product_id = product.id
        db.commit()
        return order
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/public/orders/{public_token}", response_model=OrderRead)
def public_order(public_token: str, response: Response, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.public_token == public_token))
    if not order or order.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=404, detail="订单不存在")
    response.set_cookie("forpay_checkout", checkout_session_value(public_token), max_age=max(60, int((order.expires_at - datetime.now(UTC)).total_seconds())), httponly=True, secure=get_settings().environment != "development", samesite="strict")
    return order


def _require_checkout_session(public_token: str, value: str | None) -> None:
    expected = checkout_session_value(public_token)
    if not value or not secrets.compare_digest(expected, value):
        raise HTTPException(status_code=403, detail="checkout session required")


@router.get("/public/orders/{public_token}/qr")
def public_order_qr(public_token: str, request: Request, db: Session = Depends(get_db)):
    from pathlib import Path

    from fastapi.responses import FileResponse
    order = db.scalar(select(Order).where(Order.public_token == public_token))
    if not order or order.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=404, detail="二维码已失效")
    _require_checkout_session(public_token, request.cookies.get("forpay_checkout"))
    channel = db.get(PaymentChannel, order.channel_id)
    filename = Path(channel.qr_code_url or "").name if channel else ""
    target = Path("data/qr") / filename
    if not filename or not target.is_file():
        raise HTTPException(status_code=404, detail="二维码尚未配置")
    return FileResponse(target, headers={"Cache-Control": "no-store"})


@router.get("/public/orders/{public_token}/checkout-qr")
def checkout_qr(public_token: str, request: Request, db: Session = Depends(get_db)):
    from io import BytesIO

    import qrcode
    from fastapi.responses import StreamingResponse
    order = db.scalar(select(Order).where(Order.public_token == public_token))
    if not order or order.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=404, detail="订单已失效")
    _require_checkout_session(public_token, request.cookies.get("forpay_checkout"))
    url = f"{get_settings().public_base_url}/pay/{order.public_token}"
    image = qrcode.make(url)
    stream = BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return StreamingResponse(stream, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/admin/login")
def admin_login(payload: AdminLogin, response: Response):
    if not secrets.compare_digest(payload.token, get_settings().admin_token):
        raise HTTPException(status_code=401, detail="管理令牌无效")
    response.set_cookie(
        "forpay_admin",
        admin_session_value(),
        max_age=3600,
        httponly=True,
        secure=get_settings().environment != "development",
        samesite="strict",
    )
    return {"authenticated": True}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.count(Order.id))) or 0
    paid = db.scalar(select(func.count(Order.id)).where(Order.status == "paid")) or 0
    waiting = db.scalar(select(func.count(Order.id)).where(Order.status == "waiting_payment")) or 0
    amount = db.scalar(select(func.coalesce(func.sum(Order.amount), 0)).where(Order.status == "paid")) or 0
    return {"orders": total, "paid_orders": paid, "waiting_orders": waiting, "paid_amount": amount}


@router.get("/admin/update/check")
async def update_check(_: None = Depends(require_admin_token)):
    try:
        return await check_update()
    except UpdateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/channels", response_model=ChannelRead, status_code=201)
def add_channel(payload: ChannelCreate, _: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    channel = PaymentChannel(**payload.model_dump())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/channels/{channel_id}/qr-upload", response_model=ChannelRead)
async def upload_qr(channel_id: int, file: UploadFile = File(...), _: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    channel = db.get(PaymentChannel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="收款通道不存在")
    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="只支持 PNG、JPEG 或 WebP 图片")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="二维码图片不能超过 5MB")
    valid_signature = (
        (file.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
        or (file.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
        or (file.content_type == "image/webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP")
    )
    if not valid_signature:
        raise HTTPException(status_code=415, detail="文件内容不是有效的图片")
    import uuid
    from pathlib import Path
    target_dir = Path("data/qr")
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".png" if file.content_type == "image/png" else ".jpg"
    target = target_dir / (uuid.uuid4().hex + suffix)
    target.write_bytes(content)
    channel.qr_code_url = "private://qr/" + target.name
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/channels", response_model=list[ChannelRead])
def list_channels(_: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    return db.scalars(select(PaymentChannel).order_by(PaymentChannel.created_at.desc())).all()


@router.post("/orders", response_model=OrderRead, status_code=201)
def add_order(payload: OrderCreate, _: None = Depends(require_admin_token), idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"), db: Session = Depends(get_db)):
    try:
        return create_order(db, payload, idempotency_key)
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(select(Order).where(Order.merchant_id == payload.merchant_id, Order.idempotency_key == idempotency_key))
            if existing:
                return existing
        raise HTTPException(status_code=409, detail="订单已存在或请求冲突") from None
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/orders", response_model=list[OrderRead])
def list_orders(limit: int = 50, db: Session = Depends(get_db)):
    return db.scalars(select(Order).order_by(Order.created_at.desc()).limit(min(max(limit, 1), 200))).all()


@router.get("/orders/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/monitor/notifications", response_model=NotificationResult, status_code=201)
def receive_notification(payload: NotificationCreate, _: None = Depends(require_monitor_token), db: Session = Depends(get_db)):
    notification = handle_notification(db, payload)
    order = db.get(Order, notification.matched_order_id) if notification.matched_order_id else None
    reason = None if order else "没有找到金额、通道和有效期都匹配的订单"
    return {"notification_id": notification.id, "match_status": notification.match_status, "order": order, "reason": reason}


@router.get("/notifications/unmatched")
def unmatched_notifications(_: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    return db.scalars(select(PaymentNotification).where(PaymentNotification.match_status == "unmatched").order_by(PaymentNotification.created_at.desc()).limit(100)).all()


@router.post("/notifications/{notification_id}/match", response_model=NotificationResult)
def manually_match(notification_id: int, payload: ManualMatch, _: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    notification = db.get(PaymentNotification, notification_id)
    order = db.get(Order, payload.order_id)
    if not notification or not order:
        raise HTTPException(status_code=404, detail="通知或订单不存在")
    if notification.match_status != "unmatched":
        raise HTTPException(status_code=409, detail="notification already processed")
    if notification.channel_id != order.channel_id or notification.amount != order.display_amount:
        raise HTTPException(status_code=409, detail="notification channel or amount mismatch")
    if order.status not in {"created", "waiting_payment", "manual_review"}:
        raise HTTPException(status_code=409, detail="订单当前状态不能补单")
    notification.match_status = "manual"
    notification.matched_order_id = order.id
    order.status = "paid"
    order.paid_at = notification.notification_time
    db.add(PaymentEvent(order_id=order.id, event_type="payment.manual_match", payload={"notification_id": notification.id, "amount": str(notification.amount)}))
    db.commit()
    queue_callback(db, order)
    return {"notification_id": notification.id, "match_status": "manual", "order": order}


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
def add_api_key(payload: ApiKeyCreate, _: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    key_id, secret = create_api_key(db, payload.merchant_id, payload.label)
    return {"key_id": key_id, "secret": secret}


@router.post("/merchant/orders", response_model=OrderRead, status_code=201)
async def merchant_order(
    payload: OrderCreate,
    request: Request,
    x_forpay_key: str = Header(...),
    x_forpay_timestamp: str = Header(...),
    x_forpay_signature: str = Header(...),
    x_idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    key = authenticate_signature(db, x_forpay_key, x_forpay_timestamp, x_forpay_signature, await request.body())
    if not key or key.merchant_id != payload.merchant_id:
        raise HTTPException(status_code=401, detail="商户密钥无效")
    try:
        return create_order(db, payload, x_idempotency_key)
    except IntegrityError:
        db.rollback()
        if x_idempotency_key:
            existing = db.scalar(select(Order).where(Order.merchant_id == payload.merchant_id, Order.idempotency_key == x_idempotency_key))
            if existing:
                return existing
        raise HTTPException(status_code=409, detail="订单已存在或请求冲突") from None


@router.post("/callbacks/{attempt_id}/retry")
async def retry_callback(attempt_id: int, _: None = Depends(require_admin_token), db: Session = Depends(get_db)):
    attempt = db.get(CallbackAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="回调任务不存在")
    success = await deliver_callback(db, attempt)
    return {"id": attempt.id, "success": success, "status": attempt.status, "attempt_count": attempt.attempt_count}


@router.post("/epay/submit.php")
async def epay_submit(
    payload: OrderCreate,
    request: Request,
    x_forpay_key: str = Header(...),
    x_forpay_timestamp: str = Header(...),
    x_forpay_signature: str = Header(...),
    x_idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    key = authenticate_signature(db, x_forpay_key, x_forpay_timestamp, x_forpay_signature, await request.body())
    if not key or key.merchant_id != payload.merchant_id:
        raise HTTPException(status_code=401, detail="商户签名无效")
    try:
        order = create_order(db, payload, x_idempotency_key)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"code": 1, "msg": "ok", "trade_no": order.out_trade_no, "payurl": f"/pay/{order.id}", "money": str(order.display_amount)}
