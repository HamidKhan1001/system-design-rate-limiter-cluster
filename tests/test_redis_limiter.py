import pytest
import fakeredis
from limiter import RedisRateLimiter


@pytest.fixture
def redis():
    return fakeredis.FakeRedis()


@pytest.fixture
def limiter(redis):
    return RedisRateLimiter(redis, capacity=10, refill_rate=1)


def test_allows_first_request(limiter):
    assert limiter.allow("user1") is True


def test_denies_over_limit(redis):
    lim = RedisRateLimiter(redis, capacity=3, refill_rate=0.1)
    lim.allow("u", 3)
    assert lim.allow("u") is False


def test_remaining_decreases(limiter):
    limiter.allow("u2", 5)
    remaining = limiter.remaining("u2")
    assert remaining <= 5.5  # allow tiny timing float


def test_different_identifiers_independent(limiter):
    limiter.allow("a", 10)
    assert limiter.allow("b") is True


def test_remaining_full_when_not_seen(limiter):
    assert limiter.remaining("fresh") == 10.0
