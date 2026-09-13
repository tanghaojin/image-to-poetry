from typing import Any

import redis.asyncio as redis
from loguru import logger

from core.config import settings


class RedisService:
    def __init__(self) -> None:
        self.client: redis.Redis | None = None

    async def connect(self) -> bool:
        try:
            self.client = redis.from_url(settings.redis_url, decode_responses=True)
            await self.client.ping()
            return True
        except Exception as exc:
            logger.warning("Redis connection unavailable: {}", type(exc).__name__)
            self.client = None
            return False

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            return bool(await self.client.ping())
        except Exception:
            return False

    async def eval(self, script: str, keys: list[str], args: list[Any]) -> Any:
        if self.client is None:
            raise ConnectionError("Redis is not connected")
        return await self.client.eval(script, len(keys), *keys, *args)


redis_service = RedisService()

