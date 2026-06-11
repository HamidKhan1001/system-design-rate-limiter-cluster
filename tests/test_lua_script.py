from limiter import TOKEN_BUCKET_SCRIPT


def test_lua_script_is_string():
    assert isinstance(TOKEN_BUCKET_SCRIPT, str)


def test_lua_script_contains_keys():
    assert "KEYS[1]" in TOKEN_BUCKET_SCRIPT
    assert "ARGV" in TOKEN_BUCKET_SCRIPT


def test_lua_script_has_atomic_hmset():
    assert "HMSET" in TOKEN_BUCKET_SCRIPT


def test_lua_script_checks_capacity():
    assert "capacity" in TOKEN_BUCKET_SCRIPT


def test_lua_script_returns_values():
    assert "return 1" in TOKEN_BUCKET_SCRIPT
    assert "return 0" in TOKEN_BUCKET_SCRIPT
