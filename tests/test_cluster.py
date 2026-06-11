import pytest
from limiter import ClusterRateLimiter


@pytest.fixture
def cluster():
    return ClusterRateLimiter(regions=["us-east", "eu-west"], capacity=10, refill_rate=1)


def test_allows_in_region(cluster):
    assert cluster.allow("us-east", "user1") is True


def test_denies_over_limit(cluster):
    lim = ClusterRateLimiter(regions=["us"], capacity=3, refill_rate=0.1)
    lim.allow("us", "u", 3)
    assert lim.allow("us", "u") is False


def test_regions_independent(cluster):
    cluster.allow("us-east", "u", 10)
    assert cluster.allow("eu-west", "u") is True


def test_unknown_region_raises(cluster):
    with pytest.raises(KeyError):
        cluster.allow("ap-southeast", "u")


def test_add_region(cluster):
    cluster.add_region("ap-east", capacity=5, refill_rate=1)
    assert cluster.allow("ap-east", "u") is True


def test_available_positive(cluster):
    assert cluster.available("us-east") > 0


def test_empty_regions_raises():
    with pytest.raises(ValueError):
        ClusterRateLimiter(regions=[], capacity=10, refill_rate=1)
