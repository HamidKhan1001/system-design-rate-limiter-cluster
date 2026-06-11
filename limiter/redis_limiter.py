import time


class RedisRateLimiter:
    """
    Token-bucket rate limiter backed by Redis.
    Uses the Lua script logic inline (fakeredis doesn't support EVAL with scripts,
    so we emulate atomicity via WATCH/pipeline in this in-process stub).
    """

    def __init__(self, redis_client, capacity: float, refill_rate: float, key_prefix: str = "rl"):
        self._r = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._prefix = key_prefix

    def _key(self, identifier: str) -> str:
        return f"{self._prefix}:{identifier}"

    def allow(self, identifier: str, tokens: float = 1.0) -> bool:
        key = self._key(identifier)
        now = time.time()

        pipe = self._r.pipeline(True)
        try:
            pipe.watch(key)
            data = self._r.hmget(key, "tokens", "last_refill")
            current_tokens = float(data[0]) if data[0] else self.capacity
            last_refill = float(data[1]) if data[1] else now

            elapsed = max(0.0, now - last_refill)
            current_tokens = min(self.capacity, current_tokens + elapsed * self.refill_rate)

            allowed = current_tokens >= tokens
            if allowed:
                current_tokens -= tokens

            ttl = int(self.capacity / self.refill_rate) + 1
            pipe.multi()
            pipe.hset(key, mapping={"tokens": current_tokens, "last_refill": now})
            pipe.expire(key, ttl)
            pipe.execute()
            return allowed
        except Exception:
            return False

    def remaining(self, identifier: str) -> float:
        key = self._key(identifier)
        data = self._r.hmget(key, "tokens", "last_refill")
        if not data[0]:
            return self.capacity
        tokens = float(data[0])
        last = float(data[1]) if data[1] else time.time()
        elapsed = max(0.0, time.time() - last)
        return min(self.capacity, tokens + elapsed * self.refill_rate)
