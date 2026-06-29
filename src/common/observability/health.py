"""Health check service for Kubernetes liveness and readiness probes."""

from datetime import UTC, datetime
from typing import Any

from django.core.cache import cache
from django.db import connection


class HealthCheckService:
    """Singleton health check service for all system dependencies."""

    _instance: "HealthCheckService | None" = None

    def __new__(cls) -> "HealthCheckService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def instance(cls) -> "HealthCheckService":
        return cls()

    def check_database(self) -> tuple[bool, str]:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True, "Database connection OK"
        except Exception as e:
            return False, f"Database error: {e!s}"

    def check_redis(self) -> tuple[bool, str]:
        try:
            cache.set("health_check_test", "ok", 10)
            if cache.get("health_check_test") == "ok":
                return True, "Redis connection OK"
            return False, "Redis set/get failed"
        except Exception as e:
            return False, f"Redis error: {e!s}"

    def liveness_probe(self) -> dict[str, Any]:
        """In-process liveness check — no external calls."""
        return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}

    async def readiness_probe(self) -> dict[str, Any]:
        return {"status": "ready", "timestamp": datetime.now(UTC).isoformat()}
        # from asgiref.sync import sync_to_async
        #
        # try:
        #     db_ok, db_msg = await sync_to_async(self.check_database)()
        #     redis_ok, redis_msg = await sync_to_async(self.check_redis)()
        #     is_ready = db_ok and redis_ok
        #     payload: dict[str, Any] = {
        #         "status": "ready" if is_ready else "not_ready",
        #         "timestamp": datetime.now(UTC).isoformat(),
        #         "checks": {"database": db_msg, "redis": redis_msg},
        #     }
        #     if not is_ready:
        #         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
        #     return payload
        # except HTTPException:
        #     raise
        # except Exception as e:
        #     raise HTTPException(
        #         status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        #         detail={"status": "not_ready", "error": str(e), "timestamp": datetime.now(UTC).isoformat()},
        #     )
