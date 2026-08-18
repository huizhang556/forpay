from app.main import app
from app.services.orders import _validate_callback_url
from app.services.security import checkout_session_value
from fastapi.testclient import TestClient


def test_security_headers_are_present():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_monitor_ingestion_requires_token():
    response = TestClient(app).post(
        "/api/monitor/notifications",
        json={"channel_id": 1, "external_id": "anonymous", "amount": "1.00"},
    )
    assert response.status_code == 401


def test_callback_url_rejects_private_networks():
    try:
        _validate_callback_url("http://127.0.0.1/internal")
    except ValueError:
        return
    raise AssertionError("private callback URL was accepted")


def test_checkout_session_is_order_bound():
    first = checkout_session_value("order-a")
    assert first != checkout_session_value("order-b")
    assert len(first) == 64
