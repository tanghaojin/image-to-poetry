import hashlib
import hmac
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.common.services.redis_service import RedisService, redis_service
from core.config import settings
from core.errors import ApiError, ERRORS


FINGERPRINT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
local limit = tonumber(ARGV[1])
local allowed = 0
if current <= limit then
  allowed = 1
end
local remaining = limit - current
if remaining < 0 then
  remaining = 0
end
return {allowed, current, remaining}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    used: int
    remaining: int


class FingerprintRateLimiter:
    def __init__(self, redis: RedisService = redis_service) -> None:
        self.redis = redis

    @staticmethod
    def validate_fingerprint(fingerprint: str | None) -> str:
        value = (fingerprint or "").strip()
        if not FINGERPRINT_PATTERN.fullmatch(value):
            raise ApiError(ERRORS["DEVICE_FINGERPRINT_MISSING"])
        return value

    @staticmethod
    def _fingerprint_hash(fingerprint: str) -> str:
        return hmac.new(
            settings.fingerprint_hash_secret.encode("utf-8"),
            fingerprint.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _bucket(now: datetime | None = None) -> tuple[str, int]:
        timezone = ZoneInfo(settings.rate_limit_timezone)
        current = now.astimezone(timezone) if now else datetime.now(timezone)
        next_midnight = datetime.combine(
            current.date() + timedelta(days=1), datetime.min.time(), tzinfo=timezone
        )
        ttl_seconds = max(1, math.ceil((next_midnight - current).total_seconds()))
        return current.strftime("%Y%m%d"), ttl_seconds

    async def consume(
        self, fingerprint: str | None, now: datetime | None = None
    ) -> RateLimitResult:
        validated = self.validate_fingerprint(fingerprint)
        if not settings.rate_limit_enabled:
            return RateLimitResult(True, 0, settings.rate_limit_daily)

        date_bucket, ttl_seconds = self._bucket(now)
        digest = self._fingerprint_hash(validated)
        key = f"{settings.redis_key_prefix}:quota:{digest}:{date_bucket}"

        try:
            raw = await self.redis.eval(
                RATE_LIMIT_SCRIPT,
                [key],
                [settings.rate_limit_daily, ttl_seconds],
            )
        except Exception as exc:
            raise ApiError(ERRORS["DEPENDENCY_UNAVAILABLE"]) from exc

        result = RateLimitResult(bool(int(raw[0])), int(raw[1]), int(raw[2]))
        if not result.allowed:
            raise ApiError(ERRORS["SERVER_BUSY"])
        return result


fingerprint_rate_limiter = FingerprintRateLimiter()

