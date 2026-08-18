from datetime import datetime
from decimal import Decimal

from app.models.payment import ChannelType, OrderStatus
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ChannelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    channel_type: ChannelType
    account_label: str = Field(min_length=2, max_length=120)
    qr_code_url: str | None = None


class ChannelRead(ChannelCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    enabled: bool
    created_at: datetime


class OrderCreate(BaseModel):
    merchant_id: str = Field(default="default", max_length=80)
    out_trade_no: str | None = Field(default=None, max_length=64)
    subject: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=Decimal("0"), decimal_places=2)
    channel_id: int
    notify_url: AnyHttpUrl | None = None
    return_url: AnyHttpUrl | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: str
    out_trade_no: str
    subject: str
    amount: Decimal
    display_amount: Decimal
    channel_id: int
    status: OrderStatus
    notify_url: str | None
    return_url: str | None
    paid_at: datetime | None
    expires_at: datetime
    created_at: datetime
    public_token: str
    product_id: int | None


class NotificationCreate(BaseModel):
    channel_id: int
    external_id: str = Field(min_length=1, max_length=160)
    amount: Decimal = Field(gt=Decimal("0"), decimal_places=2)
    payer_name: str | None = None
    notification_time: datetime | None = None
    raw_payload: dict = Field(default_factory=dict)


class NotificationResult(BaseModel):
    notification_id: int
    match_status: str
    order: OrderRead | None = None
    reason: str | None = None


class ApiKeyCreate(BaseModel):
    merchant_id: str = Field(default="default", max_length=80)
    label: str = Field(default="默认密钥", max_length=80)


class ApiKeyCreated(BaseModel):
    key_id: str
    secret: str


class AdminLogin(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class ManualMatch(BaseModel):
    order_id: int


class ProductCreate(BaseModel):
    merchant_id: str = Field(default="default", max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=Decimal("0"), decimal_places=2)


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    enabled: bool
    created_at: datetime


class CheckoutCreate(BaseModel):
    product_id: int
    channel_id: int
