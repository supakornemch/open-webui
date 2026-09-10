import asyncio
import base64
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "app" / "tools" / "fabric-query-delegated.py"


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


def test_query_passes_request_token_to_connection_without_fallback(monkeypatch):
    instance = tool()
    seen = {}

    def fake_query(database_name, cleaned_query, limit, offset, access_token):
        seen["token"] = access_token
        return "ok"

    monkeypatch.setattr(instance, "_sync_get_connection_and_query", fake_query)
    result = asyncio.run(
        instance.query_fabric_delegated(
            "SELECT TOP 1 BillingDate FROM dv.mlv_sale_preformance_aggregate",
            __oauth_token__={"access_token": delegated_token()},
            __user__={"id": "user-id", "email": "tester@haadthip.com"},
        )
    )
    assert result.startswith("Delegated user tester@haadthip.com")
    assert seen["token"] == delegated_token()
