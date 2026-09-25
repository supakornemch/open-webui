import asyncio
import base64
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
QUERY_TOOL_PATH = ROOT / "app" / "openwebui" / "tools" / "fabric-query-delegated.py"


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


def test_query_tool_rejects_table_not_returned_by_preflight(monkeypatch):
    """Query SQL must not execute when token-derived permission preflight excludes a table."""
    mod = load_query_tool()
    tools = mod.Tools()
    executed = []

    class Cursor:
        def execute(self, sql):
            executed.append(sql)

        def fetchall(self):
            return [("dv", "mlv_sale_preformance_aggregate")]

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            executed.append("closed")

    class Pyodbc:
        @staticmethod
        def connect(*args, **kwargs):
            return Connection()

    monkeypatch.setitem(__import__("sys").modules, "pyodbc", Pyodbc)
    result = tools._sync_get_connection_and_query(
        "LH_OTC_TEST",
        "SELECT BillingDate, Zone FROM dv.unauthorized_table WHERE Zone='South'",
        1,
        0,
        make_fake_token(),
    )

    assert "ไม่มีสิทธิ์เข้าถึงตาราง" in result
    assert len(executed) == 2


def test_query_tool_executes_only_after_preflight_allows_table(monkeypatch):
    """The permission SQL must run before the requested SQL using the same connection."""
    mod = load_query_tool()
    tools = mod.Tools()
    executed = []

    class Cursor:
        description = [("BillingDate",)]

        def execute(self, sql):
            executed.append(sql)

        def fetchall(self):
            return [("dv", "mlv_sale_preformance_aggregate")]

        def fetchmany(self, limit):
            return [("2026-09-15",)]

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            executed.append("closed")

    class Pyodbc:
        @staticmethod
        def connect(*args, **kwargs):
            return Connection()

    monkeypatch.setitem(__import__("sys").modules, "pyodbc", Pyodbc)
    sql = "SELECT BillingDate, Zone FROM dv.mlv_sale_preformance_aggregate WHERE Zone='South'"
    result = tools._sync_get_connection_and_query("LH_OTC_TEST", sql, 1, 0, make_fake_token())

    assert result.startswith("Database: `LH_OTC_TEST`")
    assert "HAS_PERMS_BY_NAME" in executed[0]
    assert executed[1] == sql


def test_query_tool_rejects_wildcard_select():
    """query_fabric_delegated must reject SELECT * even if table is allowed."""
    mod = load_query_tool()
    tools = mod.Tools()
    
    fake_token = make_fake_token()
    oauth_token = {"access_token": fake_token}
    user = {"email": "test@haadthip.com"}
    wildcard_sql = "SELECT * FROM dv.mlv_sale_preformance_aggregate"

    result = asyncio.run(
        tools.query_fabric_delegated(
            sql_query=wildcard_sql,
            __oauth_token__=oauth_token,
            __user__=user,
        )
    )
    
    assert "SELECT *" in result or "wildcard" in result.lower()


def test_query_tool_always_preflights_permissions(monkeypatch):
    """The public tool call cannot opt out of the permission preflight."""
    mod = load_query_tool()
    tools = mod.Tools()
    seen = {}

    def fake_query(database_name, cleaned_query, limit, offset, access_token):
        seen["token"] = access_token
        return "permission preflight complete"

    monkeypatch.setattr(tools, "_sync_get_connection_and_query", fake_query)
    result = asyncio.run(
        tools.query_fabric_delegated(
            sql_query="SELECT BillingDate FROM dv.mlv_sale_preformance_aggregate",
            __oauth_token__={"access_token": make_fake_token()},
            __user__={"email": "test@haadthip.com"},
        )
    )

    assert result.startswith("Delegated user")
    assert seen["token"] == make_fake_token()
