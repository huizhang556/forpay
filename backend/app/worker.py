import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import CallbackAttempt
from app.services.callbacks import deliver_callback
from app.services.orders import expire_orders


async def process_callbacks() -> None:
    db = SessionLocal()
    try:
        attempts = db.scalars(
            select(CallbackAttempt)
            .where(CallbackAttempt.status == "pending", CallbackAttempt.next_retry_at <= datetime.now(UTC))
            .order_by(CallbackAttempt.next_retry_at)
            .limit(20)
            .with_for_update(skip_locked=True)
        ).all()
        for attempt in attempts:
            await deliver_callback(db, attempt)
    finally:
        db.close()


def process_expired_orders() -> None:
    db = SessionLocal()
    try:
        expire_orders(db)
    finally:
        db.close()


async def main() -> None:
    while True:
        try:
            await process_callbacks()
            process_expired_orders()
        except Exception:
            await asyncio.sleep(2)
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
