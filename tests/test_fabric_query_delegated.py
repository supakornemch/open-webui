import asyncio
import base64
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "app" / "openwebui" / "tools" / "fabric-query-delegated.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fabric_query_delegated", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def jwt(payload: dict) -> str:
    def enc(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc(payload)}.unsigned"


def delegated_token(**overrides) -> str:
    payload = {
        "aud": "https://database.windows.net",
        "tid": "5045d9c3-3b0b-4315-8594-64118bbd7495",
        "oid": "11111111-2222-3333-4444-555555555555",
        "scp": "user_impersonation",
        "preferred_username": "tester@haadthip.com",
    }
    payload.update(overrides)
    return jwt(payload)


def tool():
    module = load_tool_module()
    instance = module.Tools()
    instance.valves.ALLOWED_TENANT_ID = "5045d9c3-3b0b-4315-8594-64118bbd7495"
    return instance


def test_requires_open_webui_oauth_token():
    with pytest.raises(RuntimeError, match="delegated OAuth token"):
        tool()._require_delegated_token(None, {"id": "user-id"})


def test_rejects_app_only_token_without_scp():
    with pytest.raises(RuntimeError, match="delegated scope"):
        tool()._require_delegated_token(
            {"access_token": delegated_token(scp=None, roles=["Some.App.Role"])},
            {"id": "user-id"},
        )


def test_rejects_non_fabric_sql_audience():
    with pytest.raises(RuntimeError, match="audience"):
        tool()._require_delegated_token(
            {"access_token": delegated_token(aud="https://graph.microsoft.com")},
            {"id": "user-id"},
        )


def test_rejects_wrong_tenant():
    with pytest.raises(RuntimeError, match="tenant"):
        tool()._require_delegated_token(
            {"access_token": delegated_token(tid="00000000-0000-0000-0000-000000000000")},
            {"id": "user-id"},
        )


def test_accepts_verified_delegated_sql_token_and_returns_identity():
    token, identity = tool()._require_delegated_token(
        {"access_token": delegated_token()},
        {"id": "user-id", "email": "tester@haadthip.com"},
    )
    assert token.count(".") == 2
    assert identity == {
        "oid": "11111111-2222-3333-4444-555555555555",
        "tid": "5045d9c3-3b0b-4315-8594-64118bbd7495",
        "username": "tester@haadthip.com",
    }


def test_query_preflights_current_token_permissions_before_executing_sql(monkeypatch):
    instance = tool()
    seen = []

    class Cursor:
        description = [("BillingDate",)]

        def execute(self, sql):
            seen.append(sql)

        def fetchall(self):
            return [("dv", "mlv_sale_preformance_aggregate")]

        def fetchmany(self, limit):
            return [("2026-09-15",)]

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            seen.append("closed")

    class Pyodbc:
        @staticmethod
        def connect(*args, **kwargs):
            return Connection()

    monkeypatch.setitem(__import__("sys").modules, "pyodbc", Pyodbc)
    result = instance._sync_get_connection_and_query(
        "LH_OTC_TEST",
        "SELECT BillingDate FROM dv.mlv_sale_preformance_aggregate",
        1,
        0,
        delegated_token(),
    )

    assert result.startswith("Database: `LH_OTC_TEST`")
    assert "HAS_PERMS_BY_NAME" in seen[0]
    assert seen[1] == "SELECT BillingDate FROM dv.mlv_sale_preformance_aggregate"


def test_query_denies_table_not_returned_by_token_permission_preflight(monkeypatch):
    instance = tool()
    seen = []

    class Cursor:
        def execute(self, sql):
            seen.append(sql)

        def fetchall(self):
            return [("dv", "mlv_sale_preformance_aggregate")]

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            seen.append("closed")

    class Pyodbc:
        @staticmethod
        def connect(*args, **kwargs):
            return Connection()

    monkeypatch.setitem(__import__("sys").modules, "pyodbc", Pyodbc)
    result = instance._sync_get_connection_and_query(
        "LH_OTC_TEST",
        "SELECT BillingDate FROM dv.unauthorized_table",
        1,
        0,
        delegated_token(),
    )

    assert "ไม่มีสิทธิ์เข้าถึงตาราง" in result
    assert len(seen) == 2  # permission lookup then connection close; user SQL never executes
