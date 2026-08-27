import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from app.db.session import SessionLocal
from app.models import CallbackAttempt
from app.services.callbacks import deliver_callback
from app.services.orders import expire_orders

logger = logging.getLogger(__name__)


async def process_callbacks() -> None:
    db = SessionLocal()
    try:
        attempts = db.scalars(
            select(CallbackAttempt)
            .where(
                or_(
                    CallbackAttempt.status == "pending",
                    (CallbackAttempt.status == "processing")
                    & (CallbackAttempt.processing_at <= datetime.now(UTC) - timedelta(minutes=10)),
                ),
                CallbackAttempt.next_retry_at <= datetime.now(UTC),
            )
            .order_by(CallbackAttempt.next_retry_at)
            .limit(20)
            .with_for_update(skip_locked=True)
        ).all()
        now = datetime.now(UTC)
        for attempt in attempts:
            attempt.status = "processing"
            attempt.processing_at = now
        db.commit()
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
            logger.exception("worker cycle failed")
            await asyncio.sleep(2)
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
