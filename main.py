import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.common.services.redis_service import redis_service
from app.db.session import close_database
from app.health.router import router as health_router
from app.poetry.router import router as poetry_router
from app.vision.router import router as vision_router
from core.config import settings
from core.errors import ApiError, ERRORS


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.remove()
    logger.add(sys.stdout, level="DEBUG" if settings.debug else "INFO")
    await redis_service.connect()
    logger.info("{} {} started", settings.app_name, settings.app_version)
    yield
    await redis_service.close()
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="图片理解与真实古典诗词匹配服务",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Device-Fingerprint", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.spec.status_code,
        content={
            "requestId": getattr(request.state, "request_id", None),
            "error": {
                "code": exc.spec.code,
                "message": exc.spec.message,
                "retryable": exc.spec.retryable,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error: {}", type(exc).__name__)
    spec = ERRORS["INTERNAL_ERROR"]
    return JSONResponse(
        status_code=spec.status_code,
        content={
            "requestId": getattr(request.state, "request_id", None),
            "error": {
                "code": spec.code,
                "message": spec.message,
                "retryable": spec.retryable,
                "details": None,
            },
        },
    )


app.include_router(health_router)
app.include_router(poetry_router)
app.include_router(vision_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
