#!/usr/bin/env python3
"""Sync legacy procurement records to Azure AI Search.

Creates or updates the ``procurement-legacy-prices-idx`` index with records from
the legacy Trade Marketing Materials Excel workbook.
"""

import json
import os
import sys
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    VectorSearch,
    VectorSearchProfile,
)
from openai import AzureOpenAI


INDEX_NAME = "procurement-legacy-prices-idx"
SEARCH_API_VERSION = "2024-07-01"
OPENAI_API_VERSION = "2024-10-21"
EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
RECORDS_PATH = Path(__file__).resolve().parent.parent / "procurement_legacy_prices_for_search.jsonl"

SOURCE_STRING_FIELDS = (
    "source_workbook",
    "source_sheet",
    "source_category",
    "source_item",
    "source_description",
    "source_qty",
    "source_qty_y2025",
    "source_price_y2025",
    "source_supplier_2025",
    "source_qty_y2026",
    "source_awarded_vendor",
    "source_award_notes",
    "source_history_2023_qty",
    "source_history_2023_price",
    "source_history_2024_qty",
    "source_history_2024_price",
    "source_history_2025_qty",
    "source_history_2025_price",
    "source_row_json",
    "source_vendor_1",
    "source_vendor_2",
    "source_vendor_3",
    "source_vendor_4",
    "source_vendor_5",
    "source_vendor_6",
    "source_vendor_7",
    "source_vendor_8",
    "source_vendor_9",
    "source_vendor_10",
    "source_vendor_11",
    "source_vendor_12",
    "source_vendor_13",
    "source_vendor_14",
    "source_vendor_15",
)


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name}")
    return value


def ensure_index_schema(index_client: SearchIndexClient) -> None:
    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(name="product_code", type=SearchFieldDataType.String, filterable=True, searchable=True),
        SearchField(name="product_name", type=SearchFieldDataType.String, searchable=True, retrievable=True),
        SearchField(name="category", type=SearchFieldDataType.String, filterable=True, retrievable=True),
        SearchField(name="pricing_model", type=SearchFieldDataType.String, retrievable=True),
        SearchField(name="variant_code", type=SearchFieldDataType.String, retrievable=True),
        SearchField(name="variant_description", type=SearchFieldDataType.String, searchable=True, retrievable=True),
        SearchField(name="vendor_code", type=SearchFieldDataType.String, filterable=True, retrievable=True),
        SearchField(name="vendor_name", type=SearchFieldDataType.String, searchable=True, retrievable=True),
        SearchField(name="year", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
        SearchField(name="price", type=SearchFieldDataType.Double, filterable=True, sortable=True, retrievable=True),
        SearchField(name="qty", type=SearchFieldDataType.String, retrievable=True),
        SearchField(name="qty_min", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
        SearchField(name="qty_max", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
        SearchField(name="notes", type=SearchFieldDataType.String, searchable=True, retrievable=True),
        SearchField(name="product_description", type=SearchFieldDataType.String, searchable=True, retrievable=True),
        SearchField(name="related_products", type=SearchFieldDataType.Collection(SearchFieldDataType.String), retrievable=True),
        SearchField(name="corpus", type=SearchFieldDataType.String, filterable=True, retrievable=True),
        SearchField(name="source", type=SearchFieldDataType.String, retrievable=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="hnsw-profile",
        ),
    ]
    fields.extend(
        SearchField(
            name=name,
            type=SearchFieldDataType.String,
            searchable=name != "source_row_json",
            filterable=name in {"source_workbook", "source_sheet", "source_category", "source_item"},
            retrievable=True,
        )
        for name in SOURCE_STRING_FIELDS
    )
    fields.extend(
        [
            SearchField(
                name="source_header_row",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
                retrievable=True,
            ),
            SearchField(
                name="source_row",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
                retrievable=True,
            ),
            SearchField(
                name="source_awarded_price",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                retrievable=True,
            ),
        ]
    )

    vector_search = VectorSearch(
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-config")],
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
    )

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)

    try:
        existing = index_client.get_index(INDEX_NAME)
    except ResourceNotFoundError:
        index_client.create_index(index)
        print(f"Created index: {INDEX_NAME}")
        return

    existing_field_names = {field.name for field in existing.fields}
    new_field_names = {field.name for field in fields}
    missing_field_names = new_field_names - existing_field_names
    if missing_field_names:
        index_client.create_or_update_index(index)
        print(f"Updated index schema: {', '.join(sorted(missing_field_names))}")


def generate_embeddings(client: AzureOpenAI, texts: list[str]) -> list[list[float]]:
    embeddings = []
    for start in range(0, len(texts), 100):
        response = client.embeddings.create(
            input=texts[start : start + 100],
            model=EMBEDDING_DEPLOYMENT,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


def main() -> int:
    if not RECORDS_PATH.exists():
        print(f"Records file not found: {RECORDS_PATH}")
        print("Run build_legacy_records.py first")
        return 1

    search_endpoint = required("AZURE_SEARCH_ENDPOINT").rstrip("/")
    search_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY") or required("AZURE_SEARCH_KEY")
    openai_endpoint = required("OPENAI_API_BASE_URL").rstrip("/")
    openai_key = required("OPENAI_API_KEY")
    openai_api_version = os.environ.get("OPENAI_API_VERSION", OPENAI_API_VERSION)

    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=AzureKeyCredential(search_key),
        api_version=SEARCH_API_VERSION,
    )
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(search_key),
        api_version=SEARCH_API_VERSION,
    )
    openai_client = AzureOpenAI(
        api_key=openai_key,
        api_version=openai_api_version,
        azure_endpoint=openai_endpoint,
    )

    ensure_index_schema(index_client)

    records = [json.loads(line) for line in RECORDS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(records)} record(s) from {RECORDS_PATH.name}")

    texts = [record["content"] for record in records]
    embeddings = generate_embeddings(openai_client, texts)
    print(f"Generated {len(embeddings)} embedding(s)")

    for record, embedding in zip(records, embeddings):
        record["content_vector"] = embedding

    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        search_client.upload_documents(documents=batch)
        print(f"Indexed {min(i + batch_size, len(records))}/{len(records)}")

    # Remove stale records
    result = search_client.search(
        search_text="*",
        filter="corpus eq 'procurement-legacy-prices'",
        select=["id", "source"],
        top=1000,
    )
    current_ids = {record["id"] for record in records}
    stale = [{"id": doc["id"]} for doc in result if doc["id"] not in current_ids]
    if stale:
        search_client.delete_documents(documents=stale)
        print(f"Removed {len(stale)} stale legacy record(s)")

    # Verification query
    verification = search_client.search(
        search_text="*",
        filter="corpus eq 'procurement-legacy-prices'",
        top=3,
        select=["product_name", "category", "price"],
    )
    verification_results = list(verification)
    print(f"Complete: {len(records)} records upserted, {len(stale)} stale legacy records removed; verification returned {len(verification_results)} result(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
