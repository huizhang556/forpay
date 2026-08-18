import time

from app.services.security import checkout_session_value


def test_checkout_token_generation_baseline():
    started = time.perf_counter()
    for index in range(1000):
        checkout_session_value(f"order-{index}")
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0
