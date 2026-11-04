"""Additional unit tests boosting coverage across safety, rate limit, tools, and validator modules."""

import time
import duckdb
import pytest
import respx
import httpx

from app.core.rate_limit import TokenBucketRateLimiter
from app.safety.relationship_guard import reliable_relationships, validate_base_joins
from app.llm.validator import (
    ValidationResult,
    check_validation_rate_limit,
    validate_user_api_key,
    _VALIDATION_ATTEMPTS,
)
from app.tools.chart_tool import ChartTool
from app.tools.sql_tool import SQLTool
from app.tools.pandas_tool import PandasTool


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(capacity=2, refill_rate_per_sec=10.0)
    assert limiter.acquire("test_client", 1) is True
    assert limiter.acquire("test_client", 1) is True
    assert limiter.acquire("test_client", 1) is False
    time.sleep(0.15)
    assert limiter.acquire("test_client", 1) is True


def test_relationship_guard_on_duckdb(tmp_path):
    db_file = str(tmp_path / "test_rel.duckdb")
    con = duckdb.connect(db_file)
    con.execute("CREATE TABLE orders (order_id VARCHAR PRIMARY KEY, cust_id VARCHAR, amount DOUBLE)")
    con.execute("CREATE TABLE customers (cust_id VARCHAR PRIMARY KEY, name VARCHAR)")
    con.execute("INSERT INTO customers VALUES ('C1', 'Alice'), ('C2', 'Bob')")
    con.execute("INSERT INTO orders VALUES ('O1', 'C1', 100.0), ('O2', 'C2', 200.0)")
    con.close()

    rels = reliable_relationships(db_file, ["orders", "customers"])
    assert isinstance(rels, list)

    # Valid join query
    sql = 'SELECT o.order_id, c.name FROM orders o JOIN customers c ON o.cust_id = c.cust_id'
    validated = validate_base_joins(sql, db_file, ["orders", "customers"])
    assert isinstance(validated, list)

    # Query without joins
    simple_sql = 'SELECT order_id FROM orders'
    assert validate_base_joins(simple_sql, db_file, ["orders"]) == []


def test_validator_model_and_rate_limits():
    res = ValidationResult(valid=True, status="active", message="Connected", models=["model-1"])
    d = res.to_dict()
    assert d["valid"] is True
    assert d["status"] == "active"
    assert d["models"] == ["model-1"]

    uid = 99999
    _VALIDATION_ATTEMPTS[uid] = []
    for _ in range(15):
        assert check_validation_rate_limit(uid) is True
    assert check_validation_rate_limit(uid) is False


@pytest.mark.asyncio
async def test_validate_user_api_key_inputs():
    # Blank key
    r = await validate_user_api_key("openai", "")
    assert r.valid is False
    assert r.status == "invalid_key"

    # Unsupported provider
    r = await validate_user_api_key("nonexistent_provider_xyz", "key123")
    assert r.valid is False
    assert r.status == "provider_error"

    # Custom without base_url
    r = await validate_user_api_key("custom", "key123", base_url="")
    assert r.valid is False
    assert r.status == "invalid_key"

    # SSRF blocked URL
    r = await validate_user_api_key("custom", "key123", base_url="http://169.254.169.254/latest/meta-data/")
    assert r.valid is False
    assert r.status == "network_blocked"


@pytest.mark.asyncio
@respx.mock
async def test_validate_gemini_mocked():
    respx.get("https://generativelanguage.googleapis.com/v1beta/models?key=valid_key").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "models/gemini-1.5-flash"}, {"name": "models/gemini-1.5-pro"}]})
    )
    res = await validate_user_api_key("gemini", "valid_key")
    assert res.valid is True
    assert res.status == "active"

    # 400 invalid key
    respx.get("https://generativelanguage.googleapis.com/v1beta/models?key=bad_key").mock(
        return_value=httpx.Response(400, json={"error": {"message": "API_KEY_INVALID"}})
    )
    res_bad = await validate_user_api_key("gemini", "bad_key")
    assert res_bad.valid is False
    assert res_bad.status == "invalid_key"


@pytest.mark.asyncio
@respx.mock
async def test_validate_anthropic_mocked():
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={"id": "msg_123", "content": []})
    )
    res = await validate_user_api_key("anthropic", "valid_key")
    assert res.valid is True
    assert res.status == "active"

    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(401, json={"error": {"message": "invalid_api_key"}})
    )
    res_bad = await validate_user_api_key("anthropic", "bad_key")
    assert res_bad.valid is False
    assert res_bad.status == "invalid_key"


@pytest.mark.asyncio
@respx.mock
async def test_validate_openai_compat_mocked():
    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]})
    )
    res = await validate_user_api_key("openai", "sk-proj-valid")
    assert res.valid is True
    assert res.status == "active"

    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(429, json={"error": {"message": "insufficient_quota"}})
    )
    res_quota = await validate_user_api_key("openai", "sk-proj-quota")
    assert res_quota.valid is False
    assert res_quota.status in ("rate_limited", "quota_exhausted")


def test_chart_tool_picker():
    tool = ChartTool()
    # Time series -> line
    assert tool.pick_chart_type(["order_date", "sales"], [{"order_date": "2024-01-01", "sales": 100}]) == "line"
    # Share -> pie
    assert tool.pick_chart_type(["category", "share"], [{"category": "A", "share": 0.5}]) == "pie"
    # Correlation -> scatter
    assert tool.pick_chart_type(["price", "quantity"], [{"price": 10.0, "quantity": 5}]) == "scatter"
    # Comparison -> bar
    assert tool.pick_chart_type(["region", "revenue"], [{"region": "NA", "revenue": 100}]) == "bar"


def test_sql_tool_error_handling(tmp_path):
    db_file = str(tmp_path / "sql_test.duckdb")
    con = duckdb.connect(db_file)
    con.execute("CREATE TABLE items (id INT, price DOUBLE)")
    con.close()

    tool = SQLTool(db_path=db_file, allowed_tables=["items"])
    # Disallowed table
    with pytest.raises(Exception):
        tool.execute("SELECT * FROM secret_table")
