from fastapi import APIRouter
from sqlalchemy import text

from app.common.services.redis_service import redis_service
from app.db.session import AsyncSessionFactory


router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readiness() -> dict[str, object]:
    database_ready = False
    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
        database_ready = True
    except Exception:
        database_ready = False

    redis_ready = await redis_service.ping()
    return {
        "status": "ready" if database_ready and redis_ready else "not_ready",
        "dependencies": {"database": database_ready, "redis": redis_ready},
    }

