# system-design-rate-limiter-cluster

Distributed rate-limiting infrastructure for microservices meshes. Uses token-bucket algorithm with atomic Lua scripting on Redis to prevent token-sync race conditions across multi-region nodes.

## The race condition problem

Without atomicity, two concurrent requests can both read `tokens=1`, both decide to allow, and both decrement — resulting in -1 tokens. Redis Lua scripts execute as a single atomic unit, eliminating this TOCTOU race.

## Lua script (atomic token-bucket)

```lua
-- KEYS[1]=bucket, ARGV={capacity, rate, now, requested}
local tokens = redis.call('HMGET', key, 'tokens', 'last_refill')
-- refill based on elapsed time
tokens = min(capacity, tokens + elapsed * rate)
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', ...)   -- single atomic write
    return 1  -- allowed
end
return 0  -- denied
```

All reads and writes happen inside one `EVAL` call — Redis guarantees no other command runs between them.

## Components

| Class | Role |
|-------|------|
| `TokenBucket` | In-process bucket for single-node / testing |
| `RedisRateLimiter` | Redis-backed bucket using WATCH/pipeline |
| `ClusterRateLimiter` | Multi-region limiter with per-region buckets |
| `TOKEN_BUCKET_SCRIPT` | Production Lua script for atomic Redis EVAL |

## Running tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v   # 20 tests
```
