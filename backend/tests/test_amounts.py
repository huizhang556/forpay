from decimal import Decimal

from app.schemas.payment import OrderCreate


def test_order_amount_is_decimal():
    payload = OrderCreate(subject="test", amount=Decimal("10.20"), channel_id=1)
    assert payload.amount == Decimal("10.20")
