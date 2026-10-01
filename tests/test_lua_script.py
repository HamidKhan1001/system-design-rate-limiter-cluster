"""Execute the Lua script against fakeredis (backed by a real Lua interpreter)."""
import threading

import fakeredis
import pytest

from limiter import RedisRateLimiter, TOKEN_BUCKET_SCRIPT


@pytest.fixture
def redis():
    return fakeredis.FakeRedis()


def run(redis, key, capacity, rate, now, requested):
    return int(redis.eval(TOKEN_BUCKET_SCRIPT, 1, key, capacity, rate, now, requested))


def test_new_bucket_starts_full(redis):
    assert run(redis, "k", 5, 1, 1000.0, 5) == 1
    assert run(redis, "k", 5, 1, 1000.0, 1) == 0


def test_denied_request_does_not_consume_tokens(redis):
    assert run(redis, "k", 3, 1, 1000.0, 3) == 1
    assert run(redis, "k", 3, 1, 1000.0, 2) == 0
    # one second later exactly one token has refilled
    assert run(redis, "k", 3, 1, 1001.0, 1) == 1


def test_refill_is_capped_at_capacity(redis):
    run(redis, "k", 3, 1, 1000.0, 3)
    # a long idle period refills to capacity, not beyond it
    assert run(redis, "k", 3, 1, 5000.0, 3) == 1
    assert run(redis, "k", 3, 1, 5000.0, 1) == 0


def test_bucket_key_expires(redis):
    run(redis, "k", 10, 1, 1000.0, 1)
    assert 0 < redis.ttl("k") <= 11


def test_concurrent_callers_cannot_overspend(redis):
    capacity = 50
    limiter = RedisRateLimiter(redis, capacity=capacity, refill_rate=0.001)
    allowed = []
    lock = threading.Lock()

    def worker():
        for _ in range(20):
            ok = limiter.allow("shared")
            with lock:
                allowed.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(allowed) == 200
    assert sum(allowed) == capacity
