# system-design-rate-limiter-cluster

[![CI](https://github.com/HamidKhan1001/system-design-rate-limiter-cluster/actions/workflows/ci.yml/badge.svg)](https://github.com/HamidKhan1001/system-design-rate-limiter-cluster/actions/workflows/ci.yml)

A token-bucket rate limiter in Python. `RedisRateLimiter` keeps bucket state in Redis and makes each allow/deny decision in a single Lua script, so concurrent callers sharing a bucket cannot both spend the same token.

## Problem

A naive limiter reads the token count, decides, then writes it back. Two requests that read `tokens=1` at the same moment both pass, and the bucket goes negative. With several app servers sharing one Redis, that race is easy to hit.

## Design

```
allow(identifier)
      |
      v
EVALSHA token_bucket.lua  (one atomic step inside Redis)
   1. read tokens, last_refill
   2. refill: min(capacity, tokens + elapsed * rate)
   3. if tokens >= requested: subtract, allow
   4. write tokens + last_refill, set TTL
```

Redis executes a script as one unit, so no other command touches the key between the read and the write. The bucket key expires after it has had time to refill completely, so idle identifiers do not accumulate.

| Component | Role |
|---|---|
| `TOKEN_BUCKET_SCRIPT` | The Lua script above |
| `RedisRateLimiter` | Runs the script per identifier. Fails closed by default, `fail_open=True` to allow on Redis errors |
| `TokenBucket` | In-process bucket, no Redis |
| `ClusterRateLimiter` | Local simulation of per-region buckets (see limitations) |

## Usage

```python
import redis
from limiter import RedisRateLimiter

limiter = RedisRateLimiter(redis.Redis(), capacity=100, refill_rate=10)  # burst 100, 10/s sustained

if limiter.allow("user:42"):
    handle_request()
else:
    reject_with_429()
```

## Tradeoffs and limitations

- **Client clock.** The refill timestamp is the calling host's `time.time()`. If hosts sharing a bucket have skewed clocks, refill is slightly uneven. Using Redis `TIME` inside the script would remove this.
- **Failure policy.** On a Redis error the limiter denies requests by default. That protects a downstream service but turns a Redis outage into an outage for callers. Pass `fail_open=True` for the opposite trade.
- **Single Redis.** The atomicity guarantee is per Redis instance. With Redis Cluster, all keys for one bucket live on one shard, which is fine, but there is no cross-shard or cross-region coordination.
- **`ClusterRateLimiter` is a simulation.** It holds one in-process `TokenBucket` per region and ignores the identifier. It illustrates regional limits and does not sync through Redis.
- **Tests run against fakeredis**, which executes the Lua script with a real Lua interpreter. The concurrency test shows the script is correct under many threads, but fakeredis serializes commands itself, so it is not a load test of a real Redis server.

## Running the tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v
```

28 tests: refill and cap behavior, denied requests not consuming tokens, key expiry, the failure policy, and a test where 10 threads make 200 calls against a 50-token bucket and exactly 50 are allowed.
