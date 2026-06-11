from .token_bucket import TokenBucket


class ClusterRateLimiter:
    """
    Multi-region cluster limiter: each region has its own TokenBucket.
    Uses local buckets to simulate regional token sync — in production
    each region syncs via Redis Lua script for atomic cross-node consistency.
    """

    def __init__(self, regions: list, capacity: float, refill_rate: float):
        if not regions:
            raise ValueError("Need at least one region")
        self._buckets = {r: TokenBucket(capacity, refill_rate) for r in regions}
        self.regions = regions

    def allow(self, region: str, identifier: str, tokens: float = 1.0) -> bool:
        if region not in self._buckets:
            raise KeyError(f"Unknown region: {region}")
        return self._buckets[region].consume(tokens)

    def available(self, region: str) -> float:
        return self._buckets[region].available

    def add_region(self, region: str, capacity: float, refill_rate: float) -> None:
        self._buckets[region] = TokenBucket(capacity, refill_rate)
        self.regions.append(region)
