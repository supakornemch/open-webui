from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vector_factory_exposes_openwebui_0114_client_adapter():
    factory = ROOT / "app" / "image" / "patches" / "factory.py"
    source = factory.read_text(encoding="utf-8")
    assert "def get_vector_db_client(" in source
    assert "return VECTOR_DB_CLIENT" in source
