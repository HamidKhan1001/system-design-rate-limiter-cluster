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


def test_fail_closed_when_redis_errors():
    import redis as redis_lib
    from unittest.mock import MagicMock

    client = MagicMock()
    client.register_script.return_value = MagicMock(side_effect=redis_lib.ConnectionError("down"))
    assert RedisRateLimiter(client, capacity=1, refill_rate=1).allow("u") is False


def test_fail_open_when_configured():
    import redis as redis_lib
    from unittest.mock import MagicMock

    client = MagicMock()
    client.register_script.return_value = MagicMock(side_effect=redis_lib.ConnectionError("down"))
    assert RedisRateLimiter(client, capacity=1, refill_rate=1, fail_open=True).allow("u") is True


def test_rejects_non_positive_config(redis):
    with pytest.raises(ValueError):
        RedisRateLimiter(redis, capacity=0, refill_rate=1)
