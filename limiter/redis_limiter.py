import time

import redis

from .lua_scripts import TOKEN_BUCKET_SCRIPT


class RedisRateLimiter:
    """
    Token-bucket rate limiter backed by Redis.

    Each decision runs as one Lua script (see lua_scripts.py), so concurrent
    callers sharing a bucket cannot both spend the same token.

    The refill timestamp comes from the calling process's clock. Hosts whose
    clocks disagree will refill the same bucket at slightly different rates.

    If Redis is unreachable, requests are denied unless fail_open=True.
    """

    def __init__(
        self,
        redis_client,
        capacity: float,
        refill_rate: float,
        key_prefix: str = "rl",
        fail_open: bool = False,
    ):
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("capacity and refill_rate must be positive")
        self._r = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._prefix = key_prefix
        self._fail_open = fail_open
        self._script = redis_client.register_script(TOKEN_BUCKET_SCRIPT)

    def _key(self, identifier: str) -> str:
        return f"{self._prefix}:{identifier}"

    def allow(self, identifier: str, tokens: float = 1.0) -> bool:
        try:
            result = self._script(
                keys=[self._key(identifier)],
                args=[self.capacity, self.refill_rate, time.time(), tokens],
            )
        except redis.RedisError:
            return self._fail_open
        return int(result) == 1

    def remaining(self, identifier: str) -> float:
        data = self._r.hmget(self._key(identifier), "tokens", "last_refill")
        if not data[0]:
            return self.capacity
        tokens = float(data[0])
        last = float(data[1]) if data[1] else time.time()
        elapsed = max(0.0, time.time() - last)
        return min(self.capacity, tokens + elapsed * self.refill_rate)
