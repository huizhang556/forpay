from datetime import UTC, datetime

from app.models import Order, OrderStatus, PaymentEvent, PaymentNotification
from app.schemas.payment import NotificationCreate
from app.services.callbacks import queue_callback
from sqlalchemy import select
from sqlalchemy.orm import Session


def handle_notification(db: Session, payload: NotificationCreate) -> PaymentNotification:
    existing = db.scalar(select(PaymentNotification).where(PaymentNotification.external_id == payload.external_id))
    if existing:
        return existing
    notification = PaymentNotification(
        channel_id=payload.channel_id,
        external_id=payload.external_id,
        amount=payload.amount,
        payer_name=payload.payer_name,
        raw_payload=payload.raw_payload,
        notification_time=payload.notification_time or datetime.now(UTC),
    )
    db.add(notification)
    db.flush()
    order = db.scalar(
        select(Order).where(
            Order.channel_id == payload.channel_id,
            Order.display_amount == payload.amount,
            Order.status.in_([OrderStatus.CREATED, OrderStatus.WAITING_PAYMENT]),
            Order.expires_at > datetime.now(UTC),
        ).with_for_update()
    )
    if not order:
        notification.match_status = "unmatched"
        db.commit()
        return notification
    notification.match_status = "matched"
    notification.matched_order_id = order.id
    order.status = OrderStatus.PAID
    order.paid_at = payload.notification_time or datetime.now(UTC)
    db.add(PaymentEvent(order_id=order.id, event_type="payment.received", payload={
        "notification_id": notification.id,
        "external_id": payload.external_id,
        "amount": str(payload.amount),
    }))
    db.commit()
    db.refresh(notification)
    queue_callback(db, order)
    return notification
