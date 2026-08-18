# ForPay Architecture

ForPay is intentionally a modular monolith. PostgreSQL is the source of truth for orders and payment events; Redis is reserved for short-lived locks, queues and rate limits.

## Matching rule

Each active order receives a unique display_amount per channel. A notification is matched only when channel, display amount and expiration all match. The notification is stored first and is idempotent by external_id.

Static QR collection has bounded concurrency. It must expose unmatched notifications for manual review rather than guessing.

## Security boundaries

- Admin routes require X-ForPay-Admin-Token.
- Monitor notification ingestion requires X-ForPay-Monitor-Token.
- Merchant order creation uses an HMAC-SHA256 signature over timestamp and raw request body; timestamps older than five minutes are rejected.
- X-Idempotency-Key makes retries return the original order instead of creating a second order.
- API request bodies and high-risk endpoints are rate limited and size limited.
