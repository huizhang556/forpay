from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OrderStatus(StrEnum):
    CREATED = "created"
    WAITING_PAYMENT = "waiting_payment"
    PAID = "paid"
    CALLBACK_PENDING = "callback_pending"
    CALLBACK_SUCCESS = "callback_success"
    EXPIRED = "expired"
    MANUAL_REVIEW = "manual_review"


class ChannelType(StrEnum):
    WECHAT = "wechat"
    ALIPAY = "alipay"


class PaymentChannel(Base):
    __tablename__ = "payment_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    channel_type: Mapped[ChannelType] = mapped_column(String(20))
    account_label: Mapped[str] = mapped_column(String(120))
    qr_code_url: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[list["Order"]] = relationship(back_populates="channel")
    products: Mapped[list["ProductChannel"]] = relationship(back_populates="channel")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    channels: Mapped[list["ProductChannel"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductChannel(Base):
    __tablename__ = "product_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    channel_id: Mapped[int] = mapped_column(ForeignKey("payment_channels.id"))
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="channels")
    channel: Mapped[PaymentChannel] = relationship(back_populates="products")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status_expires", "status", "expires_at"),
        Index("ix_orders_merchant_created", "merchant_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(80), default="default")
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), index=True)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    subject: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    display_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    channel_id: Mapped[int] = mapped_column(ForeignKey("payment_channels.id"))
    status: Mapped[OrderStatus] = mapped_column(String(30), default=OrderStatus.CREATED, index=True)
    notify_url: Mapped[str | None] = mapped_column(String(500))
    return_url: Mapped[str | None] = mapped_column(String(500))
    buyer_name: Mapped[str | None] = mapped_column(String(120))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    channel: Mapped[PaymentChannel] = relationship(back_populates="orders")
    events: Mapped[list["PaymentEvent"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order | None] = relationship(back_populates="events")


class PaymentNotification(Base):
    __tablename__ = "payment_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("payment_channels.id"))
    external_id: Mapped[str] = mapped_column(String(160), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payer_name: Mapped[str | None] = mapped_column(String(120))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    match_status: Mapped[str] = mapped_column(String(30), default="unmatched", index=True)
    matched_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    notification_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MerchantApiKey(Base):
    __tablename__ = "merchant_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(80), index=True)
    key_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(128))
    secret_encrypted: Mapped[str | None] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(80), default="默认密钥")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CallbackAttempt(Base):
    __tablename__ = "callback_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    callback_url: Mapped[str] = mapped_column(String(500))
    request_body: Mapped[dict] = mapped_column(JSONB, default=dict)
    response_status: Mapped[int | None] = mapped_column()
    response_body: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
