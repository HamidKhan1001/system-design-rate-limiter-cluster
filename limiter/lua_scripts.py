"""
Lua script executed atomically on Redis.

Redis runs a script as a single unit, so the read-refill-decrement-write
sequence cannot interleave with another client's request for the same bucket.

KEYS[1] = bucket key
ARGV[1] = capacity, ARGV[2] = refill rate (tokens/second),
ARGV[3] = now (unix seconds, float), ARGV[4] = tokens requested

Returns 1 if the request is allowed, 0 if it is denied.
"""

TOKEN_BUCKET_SCRIPT = """
local key       = KEYS[1]
local capacity  = tonumber(ARGV[1])
local rate      = tonumber(ARGV[2])
local now       = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local data        = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens      = tonumber(data[1]) or capacity
local last_refill = tonumber(data[2]) or now

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + elapsed * rate)

local allowed = 0
if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
end

redis.call('HSET', key, 'tokens', tokens, 'last_refill', now)
redis.call('EXPIRE', key, math.ceil(capacity / rate) + 1)
return allowed
"""
