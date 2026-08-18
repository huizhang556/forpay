from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app import __version__
from app.api.routes import router
from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import payment  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
settings.validate_production_secrets()
app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_limited_paths = {"/api/orders", "/api/merchant/orders", "/api/monitor/notifications", "/api/epay/submit.php", "/api/checkout"}
_redis = Redis.from_url(settings.redis_url, decode_responses=True)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
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
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else response.headers.get("Cache-Control", "public, max-age=60")
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

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
