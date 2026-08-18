import base64
import hashlib
import hmac
import secrets
import time

from app.core.config import get_settings
from app.models import MerchantApiKey
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().session_secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def create_api_key(db: Session, merchant_id: str, label: str) -> tuple[str, str]:
    key_id = "fp_" + secrets.token_urlsafe(10)
    secret = secrets.token_urlsafe(32)
    db.add(MerchantApiKey(
        merchant_id=merchant_id,
        key_id=key_id,
        secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
        secret_encrypted=_fernet().encrypt(secret.encode()).decode(),
        label=label,
    ))
    db.commit()
    return key_id, secret


def authenticate_api_key(db: Session, key_id: str, secret: str) -> MerchantApiKey | None:
    record = db.scalar(select(MerchantApiKey).where(MerchantApiKey.key_id == key_id, MerchantApiKey.enabled.is_(True)))
    if record and secrets.compare_digest(record.secret_hash, hashlib.sha256(secret.encode()).hexdigest()):
        return record
    return None


def authenticate_signature(
    db: Session, key_id: str, timestamp: str, signature: str, body: bytes
) -> MerchantApiKey | None:
    try:
        stamp = int(timestamp)
    except (TypeError, ValueError):
        return None
    if abs(int(time.time()) - stamp) > 300:
        return None
    record = db.scalar(select(MerchantApiKey).where(MerchantApiKey.key_id == key_id, MerchantApiKey.enabled.is_(True)))
    if not record or not record.secret_encrypted:
        return None
    try:
        secret = _fernet().decrypt(record.secret_encrypted.encode())
    except InvalidToken:
        return None
    message = timestamp.encode() + b"." + body
    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return record if hmac.compare_digest(expected, signature) else None


def admin_session_value() -> str:
    return hmac.new(get_settings().admin_token.encode(), b"forpay-admin-session", hashlib.sha256).hexdigest()


def checkout_session_value(public_token: str) -> str:
    return hmac.new(get_settings().session_secret.encode(), b"forpay-checkout:" + public_token.encode(), hashlib.sha256).hexdigest()
