import time
import pytest
from limiter import TokenBucket


def test_allows_within_capacity():
    tb = TokenBucket(capacity=10, refill_rate=1)
    assert tb.consume(5) is True


def test_denies_over_capacity():
    tb = TokenBucket(capacity=3, refill_rate=1)
    tb.consume(3)
    assert tb.consume(1) is False


def test_refills_over_time():
    tb = TokenBucket(capacity=10, refill_rate=100)
    tb.consume(10)
    time.sleep(0.05)
    assert tb.consume(1) is True


def test_available_returns_float():
    tb = TokenBucket(capacity=5, refill_rate=1)
    assert isinstance(tb.available, float)


def test_invalid_capacity():
    with pytest.raises(ValueError):
        TokenBucket(capacity=0, refill_rate=1)


def test_invalid_rate():
    with pytest.raises(ValueError):
        TokenBucket(capacity=10, refill_rate=0)


def test_does_not_exceed_capacity():
    tb = TokenBucket(capacity=5, refill_rate=100)
    time.sleep(0.1)
    assert tb.available <= 5.0


def test_consume_fractional():
    tb = TokenBucket(capacity=10.0, refill_rate=1)
    assert tb.consume(0.5) is True
    assert tb.available <= 9.5 + 0.01
