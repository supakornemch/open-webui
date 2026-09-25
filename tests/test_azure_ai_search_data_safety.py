from pathlib import Path


CLIENT = Path(__file__).resolve().parents[1] / 'app' / 'image' / 'patches' / 'client.py'


def test_index_mismatch_fails_closed_instead_of_deleting_data():
    source = CLIENT.read_text(encoding='utf-8')
    assert 'refusing to delete existing data' in source
    assert 'mismatch:' in source


def test_namespace_documents_use_collection_scoped_storage_ids():
    source = CLIENT.read_text(encoding='utf-8')
    assert 'def _storage_id' in source
    assert "return f'{collection_name}:{item_id}'" in source
    assert 'self._storage_id(collection_name, _get(\'id\') or \'\')' in source


def test_azure_operations_check_per_document_results_and_follow_pages():
    source = CLIENT.read_text(encoding='utf-8')
    assert 'get_continuation_token' in source
    assert 'Azure AI Search upload failed' in source
    assert 'Azure AI Search delete failed' in source
