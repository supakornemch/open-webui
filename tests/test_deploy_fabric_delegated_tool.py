import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deploy" / "deploy-fabric-delegated-tool.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deploy_fabric_delegated_tool", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_delegated_tool_has_distinct_qas_id_and_source():
    module = load_module()
    body = module.build_body()
    assert body["id"] == "fabric_query_delegated_user_qas"
    assert body["name"] == "Fabric Query — Delegated User Token (QAS Experiment)"
    assert "fabric-query-delegated.py" in str(module.TOOL_FILE)
    assert "__oauth_token__" in body["content"]
    assert "ClientSecretCredential" not in body["content"]
    assert "DefaultAzureCredential" not in body["content"]
