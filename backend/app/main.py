import logging
import re
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, generate_latest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app import __version__
from app.api.health import router as health_router
from app.api.routes import router
from app.core.config import get_settings
from app.db.session import Base, async_engine, engine
from app.models import payment  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    yield
    await async_engine.dispose()
    engine.dispose()


settings = get_settings()
settings.validate_production_secrets()
app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
logger = logging.getLogger("forpay")
REQUESTS = Counter("forpay_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("forpay_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
_waf_pattern = re.compile(r"(?:union\s+select|<script|\.\./|%2e%2e|javascript:)", re.IGNORECASE)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info("request validation failed", extra={"path": request.url.path, "errors": exc.errors()})
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": "invalid request"})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": "http_error", "detail": exc.detail}, headers=exc.headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled application error", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "internal server error"})

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_limited_paths = {"/api/orders", "/api/merchant/orders", "/api/monitor/notifications", "/api/epay/submit.php", "/api/checkout"}
_redis = Redis.from_url(settings.redis_url, decode_responses=True)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if settings.waf_enabled and _waf_pattern.search(unquote(str(request.url))):
        logger.warning("waf request blocked", extra={"path": request.url.path, "client": request.client.host if request.client else "unknown"})
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "request blocked"}, status_code=403)
    content_length = int(request.headers.get("content-length", "0") or 0)
    if content_length > settings.max_body_mb * 1024 * 1024:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "请求体超过大小限制"}, status_code=413)
    if request.url.path in _rate_limited_paths or request.url.path.endswith("/qr") or request.url.path.endswith("/checkout-qr"):
        identity = request.client.host if request.client else "unknown"
        window = int(monotonic() // 60)
        redis_key = f"forpay:rate:{identity}:{request.url.path}:{window}"
        try:
            count = await _redis.incr(redis_key)
            if count == 1:
                await _redis.expire(redis_key, 61)
        except RedisError:
            now = monotonic()
            bucket = _rate_buckets[identity]
            while bucket and now - bucket[0] > 60:
                bucket.popleft()
            count = len(bucket) + 1
            bucket.append(now)
        if count > settings.rate_limit_per_minute:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "请求过于频繁，请稍后重试"}, status_code=429, headers={"Retry-After": "60"})
    started = monotonic()
    response = await call_next(request)
    REQUESTS.labels(request.method, request.url.path if request.url.path.startswith("/api/") else "frontend", str(response.status_code)).inc()
    LATENCY.labels(request.method, request.url.path if request.url.path.startswith("/api/") else "frontend").observe(monotonic() - started)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/") or request.url.path == "/metrics":
        response.headers["Cache-Control"] = "no-store"
    elif request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "public, max-age=60")
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-ForPay-Key", "X-ForPay-Timestamp", "X-ForPay-Signature", "X-ForPay-Monitor-Token", "X-Idempotency-Key", "X-ForPay-Admin-Token"],
)


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request):
    token = request.headers.get("X-ForPay-Admin-Token")
    if not token or token != settings.admin_token:
        raise HTTPException(status_code=404, detail="not found")
    return PlainTextResponse(generate_latest().decode(), media_type="text/plain; version=0.0.4")

app.include_router(router, prefix="/api")
app.include_router(health_router, prefix="/api")

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
media_dir = Path("data")
media_dir.mkdir(parents=True, exist_ok=True)
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        requested = frontend_dist / path
        if path and requested.is_file():
            return FileResponse(requested)
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        return FileResponse(frontend_dist / "index.html")
