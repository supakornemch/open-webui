#!/usr/bin/env python3
"""Create, enrich, and sync the procurement catalog to Azure AI Search.

The workbook-derived JSON is authoritative for prices, quantities, and vendors.
Optional LLM enrichment is kept in a separate cache and is used only to improve
product retrieval and clarification. One Azure AI Search document represents
one source price row/quantity tier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import requests
except ModuleNotFoundError:
    import urllib.error
    import urllib.request

    class _UrlLibResponse:
        def __init__(self, status_code: int, body: bytes):
            self.status_code = status_code
            self.text = body.decode("utf-8", errors="replace")

        def json(self) -> Any:
            return json.loads(self.text)

    class _UrlLibRequests:
        class RequestException(Exception):
            pass

        @staticmethod
        def request(method: str, url: str, **kwargs: Any) -> _UrlLibResponse:
            body = kwargs.get("json")
            data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
            request = urllib.request.Request(
                url,
                data=data,
                headers=kwargs.get("headers") or {},
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=kwargs.get("timeout")) as response:
                    return _UrlLibResponse(response.status, response.read())
            except urllib.error.HTTPError as error:
                return _UrlLibResponse(error.code, error.read())
            except urllib.error.URLError as error:
                raise _UrlLibRequests.RequestException(str(error)) from error

    requests = _UrlLibRequests()


REQUESTS_ERROR = requests.RequestException


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "Trade Marketing Materials price for Y2026.items.json"
DEFAULT_ENRICHMENT = ROOT / "procurement-enrichment.json"
INDEX_NAME = "procurement-catalog-v1"
SEARCH_API_VERSION = "2024-07-01"
DEFAULT_OPENAI_API_VERSION = "2024-10-21"
DEFAULT_EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
DEFAULT_ENRICHMENT_DEPLOYMENT = "deploy-gpt-5.4-mini"
EMBEDDING_DIMENSIONS = 3072
DATASET = "procurement-catalog"
SOURCE_VERSION = "Y2026"
EFFECTIVE_YEAR = 2026
SEARCH_BATCH_SIZE = 100
DELETE_BATCH_SIZE = 500
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60

LEGACY_INDEXES = (
    "procurement-prices-th-idx",
    "procurement-legacy-prices-idx",
)

EXCEL_ERROR_VALUES = {
    "#REF!",
    "#N/A",
    "#VALUE!",
    "#DIV/0!",
    "#NAME?",
    "#NUM!",
    "#NULL!",
}

ENRICHMENT_KEYS = {
    "product_name",
    "product_aliases",
    "product_type",
    "keywords",
    "product_specs",
    "product_conditions",
}
ENRICHMENT_METADATA_KEYS = {
    "input_hash",
    "model",
    "prompt_version",
    "enrichment_confidence",
    "enriched_at",
}
FORBIDDEN_ENRICHMENT_KEYS = {
    "price",
    "prices",
    "awarded_price",
    "vendor",
    "vendors",
    "vendor_prices",
    "quantity",
    "qty",
    "quantities",
}


def required_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise RuntimeError(f"Set one of: {', '.join(names)}")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").replace("\r", "\n")
    return " ".join(part.strip() for part in text.split("\n") if part.strip())


def normalize_key(value: Any) -> str:
    return re.sub(r"\s+", " ", normalize_text(value)).strip().casefold()


def compact_text(value: Any) -> str:
    """Normalize text for evidence matching without changing stored source text."""
    return re.sub(r"[^\w]+", "", normalize_text(value), flags=re.UNICODE).casefold()


EVIDENCE_CONNECTORS = frozenset({"and", "or", "และ", "หรือ"})


def evidence_is_source_grounded(evidence: Any, source: Any) -> bool:
    source_compact = compact_text(source)
    tokens = [
        compact_text(token)
        for token in re.findall(r"[^\W_]+", normalize_text(evidence), flags=re.UNICODE)
        if compact_text(token) and normalize_key(token) not in EVIDENCE_CONNECTORS
    ]
    return bool(tokens) and all(token in source_compact for token in tokens)


def numeric_value(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value if value == value else None
    text = normalize_text(value).replace(",", "")
    if not text or text.upper() in EXCEL_ERROR_VALUES or text in {"-", "–", "—"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def stable_key(*parts: Any) -> str:
    material = "|".join(normalize_text(part) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def logical_item_id(item: dict[str, Any]) -> str:
    source = item.get("source") or {}
    return f"{source.get('sheet', '')}:{item.get('item_number', '')}"


def source_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("name"),
        item.get("description"),
        item.get("row_description"),
        *(item.get("description_lines") or []),
    ]
    return " ".join(
        dict.fromkeys(normalize_text(part) for part in parts if normalize_text(part))
    )


def load_items(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Input JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise RuntimeError(f"Expected an object with an items array: {path}")
    if not payload["items"]:
        raise RuntimeError(f"Input contains no items: {path}")
    return payload


def validate_source(payload: dict[str, Any]) -> dict[str, int]:
    items = payload["items"]
    ids: set[str] = set()
    logical_ids: set[str] = set()
    missing_quantity = 0
    missing_award = 0
    errors: list[str] = []

    for index, item in enumerate(items, start=1):
        item_id = item.get("id")
        logical_id = logical_item_id(item)
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"item {index}: missing id")
        elif item_id in ids:
            errors.append(f"item {index}: duplicate id {item_id}")
        else:
            ids.add(item_id)
        if not logical_id.strip() or logical_id.endswith(":"):
            errors.append(f"item {index}: invalid logical item id")
        logical_ids.add(logical_id)

        quantity = item.get("quantity") or {}
        if quantity.get("value") is None:
            missing_quantity += 1
        if numeric_value(item.get("awarded_price")) is None:
            missing_award += 1

        source_json = json.dumps(item, ensure_ascii=False)
        if any(error in source_json for error in EXCEL_ERROR_VALUES):
            errors.append(f"item {item_id or index}: Excel error value leaked into source JSON")

    if errors:
        preview = "; ".join(errors[:8])
        suffix = "" if len(errors) <= 8 else f"; and {len(errors) - 8} more"
        raise RuntimeError(f"Source validation failed: {preview}{suffix}")

    return {
        "items": len(items),
        "logical_items": len(logical_ids),
        "missing_quantity": missing_quantity,
        "missing_awarded_price": missing_award,
    }


def load_enrichment(path: Path, source_sha256: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid enrichment JSON in {path}: {error}") from error
    if not isinstance(payload, dict) or payload.get("source_sha256") != source_sha256:
        raise RuntimeError(
            f"Enrichment source_sha256 does not match input JSON: {path}. "
            "Regenerate it with --enrich."
        )
    records = payload.get("items", {})
    if not isinstance(records, dict):
        raise RuntimeError(f"Enrichment items must be an object: {path}")
    return records


def save_enrichment(path: Path, source_sha256: str, records: dict[str, dict[str, Any]]) -> None:
    payload = {
        "format": "procurement-enrichment-v1",
        "source_sha256": source_sha256,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": records,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def source_excerpt(item: dict[str, Any]) -> str:
    return source_text(item)[:6000]


def enrichment_input_hash(item: dict[str, Any]) -> str:
    return stable_key(logical_item_id(item), source_excerpt(item))


def clean_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError("Enrichment list fields must be arrays")
    result = []
    for entry in value:
        text = normalize_text(entry)
        if text and text not in result:
            result.append(text)
    return result


def validate_enrichment_entries(
    value: Any, item: dict[str, Any], kind: str
) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError(f"Enrichment {kind} entries must be an array")
    result = []
    for index, entry in enumerate(value, start=1):
        if not isinstance(entry, dict):
            raise RuntimeError(f"Enrichment {kind} entry {index} must be an object")
        allowed = (
            {"name", "value", "normalized_value", "unit", "evidence", "confidence"}
            if kind == "spec"
            else {
                "type",
                "text",
                "normalized_value",
                "is_optional",
                "evidence",
                "confidence",
            }
        )
        unknown = set(entry) - allowed
        if unknown:
            raise RuntimeError(f"Unsupported {kind} fields: {', '.join(sorted(unknown))}")
        evidence = normalize_text(entry.get("evidence"))
        if not evidence:
            raise RuntimeError(f"Enrichment {kind} entry {index} has no evidence")
        confidence = entry.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise RuntimeError(f"Enrichment {kind} entry {index} has invalid confidence")
        if kind == "spec":
            normalized = {
                "name": normalize_text(entry.get("name")),
                "value": normalize_text(entry.get("value")),
                "normalized_value": normalize_text(entry.get("normalized_value")),
                "unit": normalize_text(entry.get("unit")) or None,
                "evidence": evidence,
                "confidence": float(confidence),
            }
            if not normalized["name"] or not normalized["value"]:
                raise RuntimeError(f"Enrichment spec entry {index} needs name and value")
        else:
            normalized = {
                "type": normalize_text(entry.get("type")) or "other",
                "text": normalize_text(entry.get("text")),
                "normalized_value": normalize_text(entry.get("normalized_value")),
                "is_optional": bool(entry.get("is_optional", False)),
                "evidence": evidence,
                "confidence": float(confidence),
            }
            if not normalized["text"]:
                raise RuntimeError(f"Enrichment condition entry {index} needs text")
        result.append(normalized)
    return result


def validate_enrichment(record: Any, item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RuntimeError(f"Enrichment for {logical_item_id(item)} must be an object")
    forbidden = FORBIDDEN_ENRICHMENT_KEYS.intersection(record)
    if forbidden:
        raise RuntimeError(
            f"Enrichment for {logical_item_id(item)} contains source-owned fields: "
            f"{', '.join(sorted(forbidden))}"
        )
    unknown = set(record) - ENRICHMENT_KEYS - ENRICHMENT_METADATA_KEYS
    if unknown:
        raise RuntimeError(
            f"Enrichment for {logical_item_id(item)} contains unsupported fields: "
            f"{', '.join(sorted(unknown))}"
        )

    source = compact_text(source_excerpt(item))
    result: dict[str, Any] = {}
    product_name = normalize_text(record.get("product_name"))
    result["product_name"] = product_name or normalize_text(item.get("name"))
    result["product_aliases"] = clean_string_list(record.get("product_aliases"))
    result["product_type"] = normalize_text(record.get("product_type")) or normalize_text(
        item.get("category")
    )
    result["keywords"] = clean_string_list(record.get("keywords"))
    result["product_specs"] = validate_enrichment_entries(
        record.get("product_specs"), item, "spec"
    )
    result["product_conditions"] = validate_enrichment_entries(
        record.get("product_conditions"), item, "condition"
    )

    for entry in [*result["product_specs"], *result["product_conditions"]]:
        if not evidence_is_source_grounded(entry["evidence"], source):
            raise RuntimeError(
                f"Enrichment evidence is not present in source for {logical_item_id(item)}: "
                f"{entry['evidence']}"
            )
    return result


def fallback_enrichment(item: dict[str, Any]) -> dict[str, Any]:
    name = normalize_text(item.get("name"))
    category = normalize_text(item.get("category"))
    return {
        "product_name": name,
        "product_aliases": [],
        "product_type": category,
        "keywords": list(dict.fromkeys([category, name] if name else [category])),
        "product_specs": [],
        "product_conditions": [],
    }


def logical_items(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = OrderedDict()
    for item in items:
        grouped.setdefault(logical_item_id(item), item)
    return grouped


def build_enrichment_prompt(item: dict[str, Any]) -> str:
    return (
        "You enrich a procurement catalog record for search only. Return JSON only.\n"
        "Extract facts from SOURCE TEXT; do not invent facts. Do not return prices, quantities, "
        "vendors, vendor names, award information, or calculations.\n"
        "Every product spec and condition must include evidence copied from SOURCE TEXT and a "
        "confidence between 0 and 1.\n"
        "Use this exact JSON shape:\n"
        '{"product_name":"", "product_aliases":[], "product_type":"", "keywords":[], '
        '"product_specs":[{"name":"","value":"","normalized_value":"","unit":null,'
        '"evidence":"","confidence":0.0}], '
        '"product_conditions":[{"type":"included|excluded|optional|surcharge|size_limit|color_limit|material_limit|quantity_rule|other",'
        '"text":"","normalized_value":"","is_optional":false,"evidence":"","confidence":0.0}]}\n'
        f"SOURCE TEXT:\n{source_excerpt(item)}"
    )


def request_with_retry(method: str, url: str, **kwargs: Any) -> requests.Response:
    if requests is None:
        raise RuntimeError(
            "The requests package is required for Azure operations; "
            "install the project runtime dependencies first."
        )
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code not in {408, 429, 500, 502, 503, 504}:
                return response
            last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
        except REQUESTS_ERROR as error:
            last_error = error
        if attempt < MAX_RETRIES - 1:
            time.sleep(2**attempt)
    raise RuntimeError(f"Request failed after {MAX_RETRIES} attempts: {last_error}") from last_error


def generate_enrichment(
    items: list[dict[str, Any]],
    existing: dict[str, dict[str, Any]],
    endpoint: str,
    key: str,
    api_version: str,
    deployment: str,
    checkpoint_path: Path | None = None,
    source_sha256: str = "",
) -> dict[str, dict[str, Any]]:
    records = dict(existing)
    url = (
        f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    headers = {"api-key": key, "Content-Type": "application/json"}
    grouped = logical_items(items)
    for logical_id, item in grouped.items():
        input_hash = enrichment_input_hash(item)
        cached = records.get(logical_id)
        if isinstance(cached, dict) and cached.get("input_hash") == input_hash:
            continue
        body = {
            "messages": [
                {"role": "system", "content": "Return valid JSON and no markdown."},
                {"role": "user", "content": build_enrichment_prompt(item)},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        response = request_with_retry(
            "POST", url, headers=headers, json=body, timeout=REQUEST_TIMEOUT
        )
        try:
            content = response.json()["choices"][0]["message"]["content"]
            raw_record = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Invalid enrichment response for {logical_id}: {error}") from error
        cleaned = validate_enrichment(raw_record, item)
        records[logical_id] = {
            **cleaned,
            "input_hash": input_hash,
            "model": deployment,
            "prompt_version": "procurement-enrich-v1",
            "enrichment_confidence": min(
                [
                    entry["confidence"]
                    for entry in [*cleaned["product_specs"], *cleaned["product_conditions"]]
                ]
                or [1.0]
            ),
            "enriched_at": datetime.now(timezone.utc).isoformat(),
        }
        if checkpoint_path is not None:
            save_enrichment(checkpoint_path, source_sha256, records)
        print(f"Enriched {len(records)}/{len(grouped)}: {logical_id}")
    return records


def enrichment_for_item(
    item: dict[str, Any], records: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], str, str, float | None]:
    logical_id = logical_item_id(item)
    record = records.get(logical_id)
    if record is None:
        return fallback_enrichment(item), "not_requested", "", None
    cleaned = validate_enrichment(record, item)
    status = "accepted" if record.get("model") else "provided"
    confidence = record.get("enrichment_confidence")
    if not isinstance(confidence, (int, float)):
        confidence = None
    return cleaned, status, normalize_text(record.get("input_hash")), confidence


def build_document(
    item: dict[str, Any], payload: dict[str, Any], enrichments: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    source = item.get("source") or {}
    quantity = item.get("quantity") or {}
    enrichment, enrichment_status, input_hash, enrichment_confidence = enrichment_for_item(
        item, enrichments
    )
    item_id = normalize_text(item.get("id"))
    sheet = normalize_text(source.get("sheet"))
    row = source.get("row")
    document_id = stable_key(payload["source_sha256"], sheet, row, item_id)
    source_name = normalize_text(item.get("name"))
    source_description = normalize_text(item.get("description"))
    row_description = normalize_text(item.get("row_description"))

    quotes = []
    vendor_names = []
    vendor_keys = []
    numeric_quotes: list[tuple[str, float | int]] = []
    awarded_vendor_key = normalize_key(item.get("awarded_vendor")) or None
    for quote in item.get("vendor_prices") or []:
        vendor_name = normalize_text(quote.get("vendor"))
        if not vendor_name:
            continue
        vendor_key = normalize_key(vendor_name)
        if vendor_name not in vendor_names:
            vendor_names.append(vendor_name)
        if vendor_key and vendor_key not in vendor_keys:
            vendor_keys.append(vendor_key)
        price_raw = normalize_text(quote.get("price"))
        price = numeric_value(quote.get("price"))
        if price is not None:
            numeric_quotes.append((vendor_name, price))
        quotes.append(
            {
                "vendor_name": vendor_name,
                "vendor_key": vendor_key,
                "price": price,
                "price_raw": price_raw or None,
                "is_awarded": bool(awarded_vendor_key and vendor_key == awarded_vendor_key),
                "source_column": None,
            }
        )

    lowest_quote_price = None
    lowest_quote_vendor = None
    if numeric_quotes:
        lowest_quote_vendor, lowest_quote_price = min(numeric_quotes, key=lambda pair: pair[1])
    awarded_price = numeric_value(item.get("awarded_price"))
    product_specs = enrichment["product_specs"]
    product_conditions = enrichment["product_conditions"]
    spec_text = "; ".join(
        " ".join(part for part in [spec["name"], spec["value"], spec.get("unit")] if part)
        for spec in product_specs
    )
    condition_text = "; ".join(
        condition["text"] for condition in product_conditions if condition.get("text")
    )
    condition_tags = list(
        dict.fromkeys(
            condition.get("normalized_value") or condition.get("type")
            for condition in product_conditions
            if condition.get("normalized_value") or condition.get("type")
        )
    )
    keywords = list(dict.fromkeys(enrichment["keywords"] + vendor_names + [sheet]))
    search_parts = [
        enrichment["product_name"],
        *enrichment["product_aliases"],
        *keywords,
        enrichment["product_type"],
        source_name,
        source_description,
        row_description,
        spec_text,
        condition_text,
        normalize_text(item.get("category")),
    ]
    search_text = " ".join(dict.fromkeys(part for part in search_parts if part))
    history = item.get("history") or {}
    source_raw = item.get("raw") or {}
    logical_id = logical_item_id(item)
    enrichment_record = enrichments.get(logical_id, {})
    return {
        "id": document_id,
        "dataset": DATASET,
        "logical_item_id": logical_id,
        "source_row_id": item_id,
        "source_file": normalize_text(payload.get("source_file")),
        "source_sha256": normalize_text(payload.get("source_sha256")),
        "source_sheet": sheet,
        "source_row": row,
        "item_number": normalize_text(item.get("item_number")),
        "source_version": SOURCE_VERSION,
        "effective_year": EFFECTIVE_YEAR,
        "category": normalize_text(item.get("category")),
        "source_name": source_name,
        "source_description": source_description,
        "row_description": row_description or None,
        "raw_source_json": json.dumps(source_raw, ensure_ascii=False, sort_keys=True),
        "history_json": json.dumps(history, ensure_ascii=False, sort_keys=True),
        "quantity_label": normalize_text(quantity.get("value")) or None,
        "quantity_min": quantity.get("min"),
        "quantity_max": quantity.get("max"),
        "quantity_is_exact": bool(quantity.get("is_exact", False)),
        "quantity_is_missing": quantity.get("value") is None,
        "currency_code": "THB",
        "awarded_price": awarded_price,
        "awarded_price_raw": normalize_text(item.get("awarded_price")) or None,
        "awarded_vendor": normalize_text(item.get("awarded_vendor")) or None,
        "awarded_vendor_key": awarded_vendor_key,
        "award_notes": [
            normalize_text(note)
            for note in item.get("award_notes") or []
            if normalize_text(note)
        ],
        "vendor_names": vendor_names,
        "vendor_keys": vendor_keys,
        "vendor_names_text": " ".join(vendor_names),
        "vendor_quotes": quotes,
        "lowest_quote_price": lowest_quote_price,
        "lowest_quote_vendor": lowest_quote_vendor,
        "award_matches_lowest_quote": (
            awarded_price is not None
            and lowest_quote_price is not None
            and awarded_price == lowest_quote_price
        ),
        "product_name": enrichment["product_name"],
        "product_aliases": enrichment["product_aliases"],
        "product_type": enrichment["product_type"],
        "keywords": keywords,
        "keywords_text": " ".join(keywords),
        "product_specs": product_specs,
        "product_spec_text": spec_text,
        "product_conditions": product_conditions,
        "product_condition_text": condition_text,
        "condition_tags": condition_tags,
        "search_text": search_text,
        "enrichment_status": enrichment_status,
        "enrichment_model": normalize_text(enrichment_record.get("model")) or None,
        "enrichment_prompt_version": normalize_text(
            enrichment_record.get("prompt_version")
        ) or None,
        "enrichment_input_hash": input_hash or None,
        "enrichment_confidence": enrichment_confidence,
        "enriched_at": normalize_text(enrichment_record.get("enriched_at")) or None,
    }


def build_documents(
    payload: dict[str, Any], enrichments: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    return [build_document(item, payload, enrichments) for item in payload["items"]]


def field(name: str, type_name: str, **options: Any) -> dict[str, Any]:
    value = {"name": name, "type": type_name}
    value.update(options)
    return value


def complex_field(name: str, child_fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "type": "Collection(Edm.ComplexType)", "fields": child_fields}


def index_schema() -> dict[str, Any]:
    searchable_thai = {
        "searchable": True,
        "retrievable": True,
        "analyzer": "th.microsoft",
    }
    fields = [
        field("id", "Edm.String", key=True, retrievable=True),
        field("dataset", "Edm.String", filterable=True, facetable=True, retrievable=True),
        field("logical_item_id", "Edm.String", filterable=True, retrievable=True),
        field("source_row_id", "Edm.String", filterable=True, retrievable=True),
        field("source_file", "Edm.String", filterable=True, retrievable=True),
        field("source_sha256", "Edm.String", filterable=True, retrievable=True),
        field("source_sheet", "Edm.String", filterable=True, facetable=True, retrievable=True),
        field("source_row", "Edm.Int32", filterable=True, sortable=True, retrievable=True),
        field("item_number", "Edm.String", filterable=True, retrievable=True),
        field("source_version", "Edm.String", filterable=True, retrievable=True),
        field(
            "effective_year",
            "Edm.Int32",
            filterable=True,
            facetable=True,
            sortable=True,
            retrievable=True,
        ),
        field("category", "Edm.String", **searchable_thai, filterable=True, facetable=True),
        field("source_name", "Edm.String", **searchable_thai),
        field("source_description", "Edm.String", **searchable_thai),
        field("row_description", "Edm.String", **searchable_thai),
        field("raw_source_json", "Edm.String", retrievable=True),
        field("history_json", "Edm.String", retrievable=True),
        field(
            "quantity_label",
            "Edm.String",
            searchable=True,
            retrievable=True,
            analyzer="th.microsoft",
        ),
        field("quantity_min", "Edm.Int32", filterable=True, sortable=True, retrievable=True),
        field("quantity_max", "Edm.Int32", filterable=True, sortable=True, retrievable=True),
        field("quantity_is_exact", "Edm.Boolean", filterable=True, retrievable=True),
        field("quantity_is_missing", "Edm.Boolean", filterable=True, retrievable=True),
        field("currency_code", "Edm.String", filterable=True, facetable=True, retrievable=True),
        field("awarded_price", "Edm.Double", filterable=True, sortable=True, retrievable=True),
        field("awarded_price_raw", "Edm.String", retrievable=True),
        field(
            "awarded_vendor",
            "Edm.String",
            searchable=True,
            filterable=True,
            retrievable=True,
            analyzer="th.microsoft",
        ),
        field("awarded_vendor_key", "Edm.String", filterable=True, retrievable=True),
        field("award_notes", "Collection(Edm.String)", searchable=True, retrievable=True),
        field(
            "vendor_names",
            "Collection(Edm.String)",
            searchable=True,
            filterable=True,
            retrievable=True,
        ),
        field("vendor_keys", "Collection(Edm.String)", filterable=True, retrievable=True),
        field(
            "vendor_names_text",
            "Edm.String",
            searchable=True,
            retrievable=True,
            analyzer="th.microsoft",
        ),
        complex_field(
            "vendor_quotes",
            [
                field(
                    "vendor_name",
                    "Edm.String",
                    searchable=True,
                    retrievable=True,
                    analyzer="th.microsoft",
                ),
                field("vendor_key", "Edm.String", filterable=True, retrievable=True),
                field("price", "Edm.Double", filterable=True, retrievable=True),
                field("price_raw", "Edm.String", retrievable=True),
                field("is_awarded", "Edm.Boolean", filterable=True, retrievable=True),
                field("source_column", "Edm.String", filterable=True, retrievable=True),
            ],
        ),
        field("lowest_quote_price", "Edm.Double", filterable=True, sortable=True, retrievable=True),
        field(
            "lowest_quote_vendor",
            "Edm.String",
            searchable=True,
            retrievable=True,
            analyzer="th.microsoft",
        ),
        field("award_matches_lowest_quote", "Edm.Boolean", filterable=True, retrievable=True),
        field("product_name", "Edm.String", **searchable_thai),
        field("product_aliases", "Collection(Edm.String)", searchable=True, retrievable=True),
        field(
            "product_type",
            "Edm.String",
            searchable=True,
            filterable=True,
            facetable=True,
            retrievable=True,
            analyzer="th.microsoft",
        ),
        field("keywords", "Collection(Edm.String)", searchable=True, filterable=True, retrievable=True),
        field("keywords_text", "Edm.String", searchable=True, retrievable=True, analyzer="th.microsoft"),
        complex_field(
            "product_specs",
            [
                field(
                    "name",
                    "Edm.String",
                    searchable=True,
                    filterable=True,
                    retrievable=True,
                    analyzer="th.microsoft",
                ),
                field("value", "Edm.String", searchable=True, retrievable=True, analyzer="th.microsoft"),
                field("normalized_value", "Edm.String", filterable=True, retrievable=True),
                field("unit", "Edm.String", filterable=True, retrievable=True),
                field("evidence", "Edm.String", searchable=True, retrievable=True, analyzer="th.microsoft"),
                field("confidence", "Edm.Double", filterable=True, retrievable=True),
            ],
        ),
        field("product_spec_text", "Edm.String", **searchable_thai),
        complex_field(
            "product_conditions",
            [
                field("type", "Edm.String", searchable=True, filterable=True, retrievable=True, analyzer="th.microsoft"),
                field("text", "Edm.String", searchable=True, retrievable=True, analyzer="th.microsoft"),
                field("normalized_value", "Edm.String", filterable=True, retrievable=True),
                field("is_optional", "Edm.Boolean", filterable=True, retrievable=True),
                field("evidence", "Edm.String", searchable=True, retrievable=True, analyzer="th.microsoft"),
                field("confidence", "Edm.Double", filterable=True, retrievable=True),
            ],
        ),
        field("product_condition_text", "Edm.String", **searchable_thai),
        field("condition_tags", "Collection(Edm.String)", searchable=True, filterable=True, retrievable=True),
        field("search_text", "Edm.String", **searchable_thai),
        field("enrichment_status", "Edm.String", filterable=True, facetable=True, retrievable=True),
        field("enrichment_model", "Edm.String", filterable=True, retrievable=True),
        field("enrichment_prompt_version", "Edm.String", filterable=True, retrievable=True),
        field("enrichment_input_hash", "Edm.String", filterable=True, retrievable=True),
        field("enrichment_confidence", "Edm.Double", filterable=True, sortable=True, retrievable=True),
        field("enriched_at", "Edm.DateTimeOffset", filterable=True, sortable=True, retrievable=True),
        field(
            "content_vector",
            "Collection(Edm.Single)",
            searchable=True,
            retrievable=False,
            dimensions=EMBEDDING_DIMENSIONS,
            vectorSearchProfile="procurement-vector-profile",
        ),
    ]
    return {
        "name": INDEX_NAME,
        "fields": fields,
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "procurement-hnsw",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                    },
                }
            ],
            "profiles": [
                {
                    "name": "procurement-vector-profile",
                    "algorithm": "procurement-hnsw",
                }
            ],
        },
        "semantic": {
            "configurations": [
                {
                    "name": "procurement-semantic",
                    "prioritizedFields": {
                        "titleField": {"fieldName": "product_name"},
                        "prioritizedContentFields": [
                            {"fieldName": "search_text"},
                            {"fieldName": "product_spec_text"},
                            {"fieldName": "product_condition_text"},
                            {"fieldName": "source_description"},
                        ],
                        "prioritizedKeywordsFields": [
                            {"fieldName": "keywords_text"},
                            {"fieldName": "category"},
                            {"fieldName": "vendor_names_text"},
                        ],
                    },
                }
            ]
        },
        "similarity": {"@odata.type": "#Microsoft.Azure.Search.BM25Similarity"},
    }


class SearchApi:
    def __init__(self, endpoint: str, key: str, index_name: str = INDEX_NAME):
        self.endpoint = endpoint.rstrip("/")
        self.key = key
        self.index_name = index_name
        self.headers = {"api-key": key, "Content-Type": "application/json"}

    def url(self, path: str, **params: str) -> str:
        query = {"api-version": SEARCH_API_VERSION, **params}
        encoded = "&".join(f"{key}={value}" for key, value in query.items())
        return f"{self.endpoint}{path}?{encoded}"

    def get_index(self, name: str | None = None) -> requests.Response:
        name = name or self.index_name
        return request_with_retry(
            "GET", self.url(f"/indexes/{name}"), headers=self.headers, timeout=REQUEST_TIMEOUT
        )

    def delete_index(self, name: str) -> requests.Response:
        return request_with_retry(
            "DELETE", self.url(f"/indexes/{name}"), headers=self.headers, timeout=REQUEST_TIMEOUT
        )

    def ensure_index(self, force_recreate: bool = False) -> None:
        existing = self.get_index()
        if existing.status_code == 404:
            response = request_with_retry(
                "POST",
                self.url("/indexes"),
                headers=self.headers,
                json={**index_schema(), "name": self.index_name},
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code not in {200, 201, 204}:
                raise RuntimeError(
                    f"Create index failed: HTTP {response.status_code}: {response.text[:1000]}"
                )
            print(f"Created index {self.index_name}")
            return
        if existing.status_code != 200:
            raise RuntimeError(
                f"Get index failed: HTTP {existing.status_code}: {existing.text[:1000]}"
            )
        if force_recreate:
            deleted = self.delete_index(self.index_name)
            if deleted.status_code not in {200, 204}:
                raise RuntimeError(
                    f"Delete target index failed: HTTP {deleted.status_code}: {deleted.text[:1000]}"
                )
            time.sleep(2)
            response = request_with_retry(
                "POST",
                self.url("/indexes"),
                headers=self.headers,
                json={**index_schema(), "name": self.index_name},
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code not in {200, 201, 204}:
                raise RuntimeError(
                    f"Recreate index failed: HTTP {response.status_code}: {response.text[:1000]}"
                )
            print(f"Recreated index {self.index_name}")
            return

        response = request_with_retry(
            "PUT",
            self.url(f"/indexes/{self.index_name}", allowIndexDowntime="true"),
            headers=self.headers,
            json={**index_schema(), "name": self.index_name},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code not in {200, 201, 204}:
            raise RuntimeError(
                f"Update index failed: HTTP {response.status_code}: {response.text[:1500]}"
            )
        print(f"Updated index {self.index_name} with allowIndexDowntime=true")

    def upload_batch(self, documents: list[dict[str, Any]]) -> None:
        response = request_with_retry(
            "POST",
            self.url(f"/indexes/{self.index_name}/docs/index"),
            headers=self.headers,
            json={"value": [{"@search.action": "mergeOrUpload", **document} for document in documents]},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code not in {200, 201}:
            raise RuntimeError(
                f"Document upload failed: HTTP {response.status_code}: {response.text[:1000]}"
            )
        failures = [
            result for result in response.json().get("value", []) if not result.get("status")
        ]
        if failures:
            first = failures[0]
            raise RuntimeError(
                f"Azure rejected {len(failures)} document(s): "
                f"{first.get('key')}: {first.get('errorMessage', 'unknown error')}"
            )

    def delete_documents(self, ids: Iterable[str]) -> int:
        values = list(ids)
        deleted = 0
        for start in range(0, len(values), DELETE_BATCH_SIZE):
            batch = values[start : start + DELETE_BATCH_SIZE]
            response = request_with_retry(
                "POST",
                self.url(f"/indexes/{self.index_name}/docs/index"),
                headers=self.headers,
                json={
                    "value": [{"@search.action": "delete", "id": value} for value in batch]
                },
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code not in {200, 201}:
                raise RuntimeError(
                    f"Document delete failed: HTTP {response.status_code}: {response.text[:1000]}"
                )
            failures = [
                result for result in response.json().get("value", []) if not result.get("status")
            ]
            if failures:
                raise RuntimeError(f"Azure rejected document delete: {failures[0]}")
            deleted += len(batch)
        return deleted

    def search_all_ids(self) -> set[str]:
        ids: set[str] = set()
        skip = 0
        while True:
            response = request_with_retry(
                "POST",
                self.url(f"/indexes/{self.index_name}/docs/search"),
                headers=self.headers,
                json={
                    "search": "*",
                    "filter": f"dataset eq '{DATASET}'",
                    "select": "id",
                    "top": 1000,
                    "skip": skip,
                },
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Existing document query failed: HTTP {response.status_code}: {response.text[:1000]}"
                )
            values = response.json().get("value", [])
            ids.update(value["id"] for value in values if value.get("id"))
            if len(values) < 1000:
                break
            skip += len(values)
        return ids

    def count(self) -> int:
        response = request_with_retry(
            "POST",
            self.url(f"/indexes/{self.index_name}/docs/search"),
            headers=self.headers,
            json={
                "search": "*",
                "filter": f"dataset eq '{DATASET}'",
                "top": 0,
                "count": True,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Count query failed: HTTP {response.status_code}: {response.text[:1000]}"
            )
        return int(response.json().get("@odata.count", 0))

    def sample(self, query: str = "ร่ม") -> list[dict[str, Any]]:
        response = request_with_retry(
            "POST",
            self.url(f"/indexes/{self.index_name}/docs/search"),
            headers=self.headers,
            json={
                "search": query,
                "queryType": "semantic",
                "semanticConfiguration": "procurement-semantic",
                "filter": f"dataset eq '{DATASET}'",
                "top": 3,
                "select": "id,product_name,category,quantity_label,awarded_price,awarded_vendor",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Verification query failed: HTTP {response.status_code}: {response.text[:1000]}"
            )
        return response.json().get("value", [])


def embed_texts(texts: list[str]) -> list[list[float]]:
    endpoint = required_env("AZURE_OPENAI_ENDPOINT", "OPENAI_API_BASE_URL")
    key = required_env("AZURE_OPENAI_KEY", "OPENAI_API_KEY")
    deployment = os.environ.get(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", DEFAULT_EMBEDDING_DEPLOYMENT
    )
    api_version = os.environ.get(
        "AZURE_OPENAI_API_VERSION",
        os.environ.get("OPENAI_API_VERSION", DEFAULT_OPENAI_API_VERSION),
    )
    url = (
        f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/embeddings"
        f"?api-version={api_version}"
    )
    headers = {"api-key": key, "Content-Type": "application/json"}
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), 25):
        response = request_with_retry(
            "POST",
            url,
            headers=headers,
            json={"input": texts[start : start + 25], "dimensions": EMBEDDING_DIMENSIONS},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Embedding request failed: HTTP {response.status_code}: {response.text[:1000]}"
            )
        data = sorted(response.json().get("data", []), key=lambda value: value.get("index", 0))
        batch = [value.get("embedding") for value in data]
        expected = min(25, len(texts) - start)
        if len(batch) != expected or any(
            not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS
            for vector in batch
        ):
            raise RuntimeError("Embedding response count or dimensions did not match the request")
        embeddings.extend(batch)
        print(f"Embedded {len(embeddings)}/{len(texts)} logical item(s)")
    return embeddings


def attach_embeddings(documents: list[dict[str, Any]]) -> None:
    by_logical_id: dict[str, str] = OrderedDict()
    for document in documents:
        by_logical_id.setdefault(document["logical_item_id"], document["search_text"])
    vectors = embed_texts(list(by_logical_id.values()))
    vector_by_logical_id = dict(zip(by_logical_id, vectors))
    for document in documents:
        document["content_vector"] = vector_by_logical_id[document["logical_item_id"]]


def delete_legacy_indexes(api: SearchApi) -> None:
    for name in LEGACY_INDEXES:
        response = api.get_index(name)
        if response.status_code == 404:
            print(f"Legacy index absent: {name}")
            continue
        if response.status_code != 200:
            raise RuntimeError(
                f"Cannot inspect legacy index {name}: HTTP {response.status_code}: {response.text[:1000]}"
            )
        deleted = api.delete_index(name)
        if deleted.status_code not in {200, 204}:
            raise RuntimeError(
                f"Cannot delete legacy index {name}: HTTP {deleted.status_code}: {deleted.text[:1000]}"
            )
        print(f"Deleted legacy index: {name}")


def print_dry_run(
    payload: dict[str, Any], documents: list[dict[str, Any]], stats: dict[str, int]
) -> None:
    print(f"Source: {payload['source_file']}")
    print(f"Source SHA-256: {payload['source_sha256']}")
    print(f"Rows/items: {stats['items']}")
    print(f"Logical items: {stats['logical_items']}")
    print(f"Missing quantity: {stats['missing_quantity']}")
    print(f"Missing awarded price: {stats['missing_awarded_price']}")
    print(f"Documents prepared: {len(documents)}")
    print(f"Unique document IDs: {len({document['id'] for document in documents})}")
    statuses = sorted({document["enrichment_status"] for document in documents})
    print(
        "Enrichment statuses: "
        + json.dumps(
            {
                status: sum(
                    1 for document in documents if document["enrichment_status"] == status
                )
                for status in statuses
            },
            ensure_ascii=False,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--enrichment-file", type=Path, default=DEFAULT_ENRICHMENT)
    parser.add_argument("--index", default=INDEX_NAME)
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate and build documents without Azure changes"
    )
    parser.add_argument(
        "--delete-legacy", action="store_true", help="Delete only the two approved legacy indexes"
    )
    parser.add_argument(
        "--create-or-update", action="store_true", help="Create or PUT the target index schema"
    )
    parser.add_argument(
        "--force-recreate", action="store_true", help="Delete and recreate only the target index"
    )
    parser.add_argument("--enrich", action="store_true", help="Generate missing LLM enrichment records")
    parser.add_argument("--ingest", action="store_true", help="Embed and upload source rows")
    parser.add_argument("--verify", action="store_true", help="Verify target index count and sample query")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.force_recreate and args.index != INDEX_NAME:
        raise RuntimeError("--force-recreate is allowed only for the default target index")
    if args.dry_run and any(
        [
            args.delete_legacy,
            args.create_or_update,
            args.force_recreate,
            args.ingest,
            args.verify,
        ]
    ):
        raise RuntimeError("--dry-run cannot be combined with Azure-changing or verification operations")
    if not any(
        [
            args.dry_run,
            args.delete_legacy,
            args.create_or_update,
            args.force_recreate,
            args.enrich,
            args.ingest,
            args.verify,
        ]
    ):
        raise RuntimeError("Choose an operation, for example --dry-run or --create-or-update --ingest")

    payload = load_items(args.input)
    stats = validate_source(payload)
    source_sha256 = normalize_text(payload.get("source_sha256"))
    if not source_sha256:
        raise RuntimeError("Input JSON is missing source_sha256")
    enrichments = load_enrichment(args.enrichment_file, source_sha256)

    if args.enrich:
        endpoint = required_env("AZURE_OPENAI_ENDPOINT", "OPENAI_API_BASE_URL")
        key = required_env("AZURE_OPENAI_KEY", "OPENAI_API_KEY")
        deployment = os.environ.get(
            "AZURE_OPENAI_ENRICHMENT_DEPLOYMENT", DEFAULT_ENRICHMENT_DEPLOYMENT
        )
        api_version = os.environ.get(
            "AZURE_OPENAI_API_VERSION",
            os.environ.get("OPENAI_API_VERSION", DEFAULT_OPENAI_API_VERSION),
        )
        enrichments = generate_enrichment(
            payload["items"],
            enrichments,
            endpoint,
            key,
            api_version,
            deployment,
            checkpoint_path=args.enrichment_file,
            source_sha256=source_sha256,
        )
        save_enrichment(args.enrichment_file, source_sha256, enrichments)
        print(f"Wrote enrichment cache: {args.enrichment_file}")

    documents = build_documents(payload, enrichments)
    print_dry_run(payload, documents, stats)
    if args.dry_run:
        return 0

    endpoint = required_env("AZURE_SEARCH_ENDPOINT")
    search_key = required_env("AZURE_SEARCH_ADMIN_KEY", "AZURE_SEARCH_KEY")
    api = SearchApi(endpoint, search_key, args.index)

    if args.delete_legacy:
        delete_legacy_indexes(api)
    if args.create_or_update or args.force_recreate:
        api.ensure_index(force_recreate=args.force_recreate)
    if args.ingest:
        attach_embeddings(documents)
        existing_ids = api.search_all_ids()
        expected_ids = {document["id"] for document in documents}
        for start in range(0, len(documents), SEARCH_BATCH_SIZE):
            batch = documents[start : start + SEARCH_BATCH_SIZE]
            api.upload_batch(batch)
            print(f"Indexed {min(start + SEARCH_BATCH_SIZE, len(documents))}/{len(documents)}")
        stale_ids = sorted(existing_ids - expected_ids)
        if stale_ids:
            deleted = api.delete_documents(stale_ids)
            print(f"Removed {deleted} stale procurement document(s)")
        else:
            print("No stale procurement documents")
    if args.verify:
        schema_response = api.get_index()
        if schema_response.status_code != 200:
            raise RuntimeError(
                f"Target index verification failed: HTTP {schema_response.status_code}: {schema_response.text[:1000]}"
            )
        schema = schema_response.json()
        vector_fields = [
            value for value in schema.get("fields", []) if value.get("name") == "content_vector"
        ]
        if not vector_fields or vector_fields[0].get("dimensions") != EMBEDDING_DIMENSIONS:
            raise RuntimeError("Target index content_vector dimensions are not 3072")
        count = api.count()
        if count != len(documents):
            raise RuntimeError(f"Target index count {count} does not match expected {len(documents)}")
        samples = api.sample()
        print(f"Verified {count} procurement document(s); sample results: {len(samples)}")
        print(json.dumps(samples, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, REQUESTS_ERROR) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
