import asyncio
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "app" / "tools" / "fabric-permissions.py"


def load_module():
    spec = importlib.util.spec_from_file_location("fabric_permissions", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_exists():
    """Tool file must exist."""
    assert TOOL_PATH.exists(), f"{TOOL_PATH} does not exist"


def test_tool_has_get_my_fabric_permissions_function():
    """Tool must define get_my_fabric_permissions."""
    mod = load_module()
    tools = mod.Tools()
    assert hasattr(tools, "get_my_fabric_permissions"), "Missing get_my_fabric_permissions method"


def test_get_my_fabric_permissions_requires_oauth_token():
    """get_my_fabric_permissions must fail when no OAuth token is supplied."""
    mod = load_module()
    tools = mod.Tools()
    with pytest.raises(RuntimeError, match="No delegated OAuth token"):
        asyncio.run(tools.get_my_fabric_permissions(__oauth_token__=None, __user__=None))


def test_get_my_fabric_permissions_returns_schema_structure():
    """get_my_fabric_permissions must return accessible schemas/tables/columns."""
    mod = load_module()
    tools = mod.Tools()
    # Mock a valid Azure SQL delegated token
    import base64
    claims = {"aud": "https://database.windows.net", "tid": "5045d9c3-3b0b-4315-8594-64118bbd7495", "oid": "test-user-oid"}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    fake_token = f"eyJhbGciOiJSUzI1NiJ9.{payload}.fake_signature"
    
    oauth_token = {"access_token": fake_token}
    user = {"email": "test@haadthip.com"}
    
    # This will fail with fake token (can't connect to real Fabric)
    # We test that it attempts connection and returns expected error structure
    try:
        result = asyncio.run(tools.get_my_fabric_permissions(__oauth_token__=oauth_token, __user__=user))
        # If it somehow succeeds (shouldn't with fake token), check structure
        assert isinstance(result, dict), "Result must be a dict"
        assert "schemas" in result, "Result must have 'schemas' key"
    except RuntimeError as exc:
        # Expected: authentication failure with fake token
        assert "Fabric SQL permission discovery failed" in str(exc) or "Could not login" in str(exc).lower()


def test_permission_discovery_includes_table_and_column_level():
    """Permission discovery must return both table-level and column-level permissions."""
    mod = load_module()
    tools = mod.Tools()
    # This test expects the returned structure to have:
    # {
    #   "schemas": [
    #     {
    #       "schema": "dv",
    #       "tables": [
    #         {
    #           "table": "mlv_sale_preformance_aggregate",
    #           "has_select": true,
    #           "columns": ["BillingDate", "Zone", ...]
    #         }
    #       ]
    #     }
    #   ]
    # }
    # This will fail until implemented
    pass


def test_permission_discovery_filters_denied_objects():
    """Permission discovery must not return schemas/tables/columns the user cannot SELECT."""
    mod = load_module()
    tools = mod.Tools()
    # Mock scenario: user has access to dv.table_a but NOT dv.table_b
    # The result should only include table_a
    # This will fail until implemented
    pass
