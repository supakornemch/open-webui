import asyncio
import base64
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
QUERY_TOOL_PATH = ROOT / "app" / "tools" / "fabric-query-delegated.py"


def load_query_tool():
    spec = importlib.util.spec_from_file_location("fabric_query_delegated", QUERY_TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_fake_token(aud="https://database.windows.net", tid="5045d9c3-3b0b-4315-8594-64118bbd7495", oid="test-oid"):
    """Helper to create a mock delegated token."""
    claims = {"aud": aud, "tid": tid, "oid": oid, "scp": "user_impersonation"}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJSUzI1NiJ9.{payload}.fake_signature"


def test_query_tool_rejects_query_without_allowed_tables():
    """query_fabric_delegated must reject SQL referencing tables not in allowed_tables."""
    mod = load_query_tool()
    tools = mod.Tools()
    
    fake_token = make_fake_token()
    oauth_token = {"access_token": fake_token}
    user = {"email": "test@haadthip.com"}
    
    # Simulate allowed_tables from permission discovery
    allowed_tables = ["dv.mlv_sale_preformance_aggregate", "dv.mlv_sale_target"]
    
    # SQL that references a table NOT in allowed list (use explicit columns to avoid wildcard rejection)
    unauthorized_sql = "SELECT BillingDate, Zone FROM dv.unauthorized_table WHERE Zone='South'"
    
    result = asyncio.run(
        tools.query_fabric_delegated(
            sql_query=unauthorized_sql,
            allowed_tables=allowed_tables,
            __oauth_token__=oauth_token,
            __user__=user,
        )
    )
    
    assert "ไม่มีสิทธิ์เข้าถึงตาราง" in result
    assert "unauthorized_table" in result.lower()


def test_query_tool_accepts_query_with_allowed_tables_only():
    """query_fabric_delegated must accept SQL referencing only allowed tables."""
    mod = load_query_tool()
    tools = mod.Tools()
    
    fake_token = make_fake_token()
    oauth_token = {"access_token": fake_token}
    user = {"email": "test@haadthip.com"}
    
    allowed_tables = ["dv.mlv_sale_preformance_aggregate"]
    
    # This SQL only references allowed table
    authorized_sql = "SELECT BillingDate, Zone FROM dv.mlv_sale_preformance_aggregate WHERE Zone='South'"
    
    # This will attempt connection (which fails with fake token)
    # but should NOT contain permission error about table access
    result = asyncio.run(
        tools.query_fabric_delegated(
            sql_query=authorized_sql,
            allowed_tables=allowed_tables,
            __oauth_token__=oauth_token,
            __user__=user,
        )
    )
    
    # Should NOT contain table permission error
    assert "ไม่มีสิทธิ์เข้าถึงตาราง" not in result
    # Should contain connection/auth error instead
    assert "Delegated Fabric query denied" in result or "Could not login" in result.lower()


def test_query_tool_rejects_wildcard_select():
    """query_fabric_delegated must reject SELECT * even if table is allowed."""
    mod = load_query_tool()
    tools = mod.Tools()
    
    fake_token = make_fake_token()
    oauth_token = {"access_token": fake_token}
    user = {"email": "test@haadthip.com"}
    
    allowed_tables = ["dv.mlv_sale_preformance_aggregate"]
    
    # SQL with SELECT *
    wildcard_sql = "SELECT * FROM dv.mlv_sale_preformance_aggregate"
    
    result = asyncio.run(
        tools.query_fabric_delegated(
            sql_query=wildcard_sql,
            allowed_tables=allowed_tables,
            __oauth_token__=oauth_token,
            __user__=user,
        )
    )
    
    assert "SELECT *" in result or "wildcard" in result.lower()


def test_query_tool_allowed_tables_parameter_is_optional():
    """If allowed_tables is None, query_fabric_delegated should skip authorization check (for backward compat)."""
    mod = load_query_tool()
    tools = mod.Tools()
    
    fake_token = make_fake_token()
    oauth_token = {"access_token": fake_token}
    user = {"email": "test@haadthip.com"}
    
    # When allowed_tables is None, tool should skip guardrail and attempt query
    # (This maintains backward compatibility with existing usage)
    sql = "SELECT BillingDate FROM dv.mlv_sale_preformance_aggregate"
    
    # Should NOT raise table permission error
    result = asyncio.run(
        tools.query_fabric_delegated(
            sql_query=sql,
            allowed_tables=None,
            __oauth_token__=oauth_token,
            __user__=user,
        )
    )
    
    assert "ไม่มีสิทธิ์เข้าถึงตาราง" not in result
    # Should contain connection error instead
    assert "Delegated Fabric query denied" in result or "Could not login" in result.lower()
