from datetime import datetime
from zoneinfo import ZoneInfo

import fakeredis.aioredis
import pytest

from app.common.services.rate_limiter import FingerprintRateLimiter
from app.common.services.redis_service import RedisService
from core.errors import ApiError


@pytest.mark.asyncio
async def test_fingerprint_quota_allows_100_and_rejects_101() -> None:
    service = RedisService()
    service.client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    limiter = FingerprintRateLimiter(service)
    now = datetime(2026, 9, 12, 12, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))

    last_result = None
    for _ in range(100):
        last_result = await limiter.consume("1234567890abcdef", now)

    assert last_result is not None
    assert last_result.allowed is True
    assert last_result.used == 100
    assert last_result.remaining == 0

    with pytest.raises(ApiError) as exc_info:
        await limiter.consume("1234567890abcdef", now)

    assert exc_info.value.spec.code == "SERVER_BUSY"
    await service.close()


@pytest.mark.asyncio
async def test_redis_key_does_not_contain_raw_fingerprint() -> None:
    service = RedisService()
    service.client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    limiter = FingerprintRateLimiter(service)
    fingerprint = "raw-fingerprint-123456"

    await limiter.consume(fingerprint)
    keys = [key async for key in service.client.scan_iter("*")]

    assert len(keys) == 1
    assert fingerprint not in keys[0]
    await service.close()


def test_invalid_fingerprint_is_rejected() -> None:
    with pytest.raises(ApiError) as exc_info:
        FingerprintRateLimiter.validate_fingerprint("bad value with spaces")
    assert exc_info.value.spec.code == "DEVICE_FINGERPRINT_MISSING"

