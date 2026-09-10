#!/usr/bin/env python3
"""Ingest the Catalog Master workbook into Azure AI Search (product-level).

Reads Procurement-Pricing-Assistant-Master-2026.xlsx (one sheet per category, header row 1)
and rebuilds `procurement-catalog-v1` with ONE document per logical product:

  --dry-run        build + validate documents without touching Azure
  --create-index   delete + recreate the target index (destructive)
  --enrich         generate LLM enrichment for missing logical products
  --ingest         embed + upload all product documents
  --verify         check vector dimensions / count + semantic sample query

Logical product id = {Year}:{Category}:{Item}. Each document carries:
  - tiers[] (quantity + awarded price)
  - flat aggregates price_min/max, quantity_min_all/max_all
  - product enrichment fields (name/aliases/type/keywords/spec/condition text)
  - award_vendors (from รายชื่อผู้ผ่านการประมูล), notes_text (from Note)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from convert_workbook_to_items_json import item_number
from sync_azure_ai_search import (
    EMBEDDING_DIMENSIONS,
    INDEX_NAME,
    SEARCH_BATCH_SIZE,
    SearchApi,
    attach_embeddings,
    enrichment_for_item,
    generate_enrichment,
    load_enrichment,
    logical_item_id,
    normalize_key,
    normalize_text,
    required_env,
    save_enrichment,
    stable_key,
    validate_source,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER = ROOT / "data/masters/Procurement-Pricing-Assistant-Master-2026.xlsx"
DEFAULT_ENRICHMENT = ROOT / "data/enrichment/procurement-enrichment-master.json"

MANDATORY_COLUMNS = {
    "ปี",
    "ลำดับ",
    "รายการ",
    "จำนวนขั้นต่ำ",
    "จำนวนสูงสุด",
    "ราคาที่ผ่านการประมูล",
}


def py_scalar(value: Any) -> Any:
    """Unwrap numpy scalars (pandas cell values) to plain Python types.

    NaN cells (blank Excel cells) are normalized to None so they never leak
    into documents as "nan" strings or NaN floats.
    """
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    try:
        if value != value:  # NaN check (float / numpy scalar)
            return None
    except (TypeError, ValueError):
        pass
    return value


def qty_int(value: Any) -> int | None:
    """Parse a quantity cell: empty / '-' / NaN -> None, else int."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "" or value == "-":
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def price_float(value: Any) -> float | None:
    """Parse a price cell: numeric -> float, otherwise None.

    The source workbook occasionally puts a text note in the awarded-price
    column (e.g. "ใช้ราคาของซัพฯที่ประมูลเสื้อได้ประเภทนั้นๆ") — such rows
    are treated as missing price (None) and the text is kept in หมายเหตุ.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_master_items(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Catalog master not found: {path}")
    xl = pd.ExcelFile(path)
    sheet_names = [name for name in xl.sheet_names if name != "Legend"]
    if not sheet_names:
        raise RuntimeError("No category sheets found in master workbook")

    items: list[dict[str, Any]] = []
    for sheet in sheet_names:
        df = xl.parse(sheet)
        missing = MANDATORY_COLUMNS - set(df.columns)
        if missing:
            raise RuntimeError(f"Sheet {sheet} missing columns: {sorted(missing)}")
        vendor_cols = [c for c in df.columns if str(c).startswith("vendor-")]

        # product-level columns: filled on the first row of a product, blank on
        # continuation tier rows -> forward-fill them (like the original workbook)
        raw_desc = df["รายการ"].copy()
        product_cols = ["ลำดับ", "รายการ", "ระยะเวลา", "การคิดราคา", "รายชื่อผู้ผ่านการประมูล", "หมายเหตุ"]
        df[product_cols] = df[product_cols].ffill()

        for idx, row in df.iterrows():
            excel_row = int(idx) + 2  # header row 1 + 0-based index
            year = int(py_scalar(row["ปี"]))
            item_no = item_number(py_scalar(row["ลำดับ"]))
            category = sheet
            if item_no is None:
                raise RuntimeError(f"{sheet} row {excel_row}: Item not resolved after ffill")
            name = normalize_text(row["รายการ"]) or None
            if not name:
                raise RuntimeError(f"{sheet} row {excel_row}: รายการ empty after ffill")

            # จำนวนขั้นต่ำ / จำนวนสูงสุด per Excel Master convention:
            #   exact 5000/5000 · range 1/10 · open 11/"-" or blank
            qmin_n = qty_int(py_scalar(row.get("จำนวนขั้นต่ำ")))
            qmax_n = qty_int(py_scalar(row.get("จำนวนสูงสุด")))
            if qmin_n is None:
                label, is_exact = None, False
            elif qmax_n is None:
                label, is_exact = f"{qmin_n}+", False
            elif qmin_n == qmax_n:
                label, is_exact = str(qmin_n), True
            else:
                label, is_exact = f"{qmin_n}-{qmax_n}", False
            quantity = {"value": label, "min": qmin_n, "max": qmax_n, "is_exact": is_exact}

            vendor_prices = []
            for col in vendor_cols:
                value = py_scalar(row[col])
                if value is None:
                    continue
                if isinstance(value, str):
                    raise RuntimeError(
                        f"{sheet} row {excel_row}: non-numeric vendor cell in {col}: {value!r}"
                    )
                # column = vendor-<n>-<name> (named) or vendor-<Category>-<n> (unnamed)
                vendor_name = col[len("vendor-"):]
                # strip leading number prefix from named columns (vendor-5-บจก.เอ -> บจก.เอ)
                num_match = re.match(r"^\d+-", vendor_name)
                if num_match:
                    vendor_name = vendor_name[num_match.end():]
                vendor_prices.append({"vendor": vendor_name, "price": float(value)})

            awarded_price = py_scalar(row["ราคาที่ผ่านการประมูล"])
            awarded_price_f = price_float(awarded_price)

            note = normalize_text(py_scalar(row.get("หมายเหตุ"))) or None
            # if the awarded-price cell held a text note, keep it in หมายเหตุ
            if awarded_price_f is None and awarded_price is not None and str(awarded_price).strip():
                price_note = normalize_text(str(awarded_price))
                note = "; ".join(x for x in [note, price_note] if x) or None
            award_vendors = [
                normalize_text(v)
                for v in str(py_scalar(row.get("รายชื่อผู้ผ่านการประมูล")) or "").split(",")
                if normalize_text(v)
            ]

            raw_row_desc = py_scalar(raw_desc[idx])
            items.append(
                {
                    "id": f"{year}:{category}:{item_no}:{excel_row}",
                    "item_number": item_no,
                    "year": year,
                    "category": category,
                    "name": name,
                    "description": name,
                    "row_description": normalize_text(raw_row_desc) or None,
                    "description_lines": [name],
                    "lead_time": normalize_text(py_scalar(row.get("ระยะเวลา"))) or "5 วัน",
                    "pricing_basis": normalize_text(py_scalar(row.get("การคิดราคา"))) or "ต่อชิ้น",
                    "note": note,
                    "award_vendors": award_vendors,
                    "history": {},
                    "quantity": quantity,
                    "vendor_prices": vendor_prices,
                    "awarded_price": awarded_price_f,
                    "source": {"sheet": category, "row": excel_row},
                    "raw": {},
                }
            )

    if not items:
        raise RuntimeError("No items produced from master")

    payload = {
        "source_file": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "format": "catalog-master-v1",
        "sheet_count": len(sheet_names),
        "item_count": len(items),
        "logical_item_count": len(
            {f"{it['year']}:{it['category']}:{it['item_number']}" for it in items}
        ),
        "items": items,
    }
    return payload


def build_product_documents(
    items: list[dict[str, Any]], enrichments: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Group tier rows into one document per logical product.

    Each document carries the agreed product-level schema: tiers[] with
    quantity and awarded price, flat aggregates, product enrichment text
    fields, award_vendors and notes_text.
    """
    from collections import OrderedDict

    groups: dict[str, list[dict[str, Any]]] = OrderedDict()
    for item in items:
        groups.setdefault(logical_item_id(item), []).append(item)

    docs: list[dict[str, Any]] = []
    for logical_id, group in groups.items():
        first = group[0]
        year = int(first["year"])
        category = first["category"]

        enrichment, _status, _input_hash, _confidence = enrichment_for_item(first, enrichments)
        product_name = enrichment["product_name"]
        aliases = enrichment["product_aliases"]
        product_type = enrichment["product_type"]
        keywords = enrichment["keywords"]
        spec_text = "; ".join(
            " ".join(part for part in [spec["name"], spec["value"], spec.get("unit")] if part)
            for spec in enrichment["product_specs"]
        )
        condition_text = "; ".join(
            condition["text"]
            for condition in enrichment["product_conditions"]
            if condition.get("text")
        )
        pricing_basis = normalize_text(first.get("pricing_basis")) or None
        note = normalize_text(first.get("note")) or None
        award_vendors = [
            normalize_text(v) for v in (first.get("award_vendors") or []) if normalize_text(v)
        ]

        tiers: list[dict[str, Any]] = []
        numeric_awards: list[float] = []
        qty_mins: list[int] = []
        qty_maxs: list[int] = []

        for item in group:
            quantity = item["quantity"]
            qmin = quantity.get("min")
            qmax = quantity.get("max")
            if qmin is not None:
                qty_mins.append(qmin)
            if qmax is not None:
                qty_maxs.append(qmax)
            awarded_price = item.get("awarded_price")
            if awarded_price is not None:
                numeric_awards.append(float(awarded_price))

            tiers.append(
                {
                    "lead_time": normalize_text(item.get("lead_time")) or "5 วัน",
                    "quantity_label": normalize_text(quantity.get("value")) or None,
                    "quantity_min": qmin,
                    "quantity_max": qmax,
                    "quantity_is_exact": bool(quantity.get("is_exact", False)),
                    "awarded_price": None if awarded_price is None else float(awarded_price),
                    "source_row": (item.get("source") or {}).get("row"),
                }
            )

        search_parts = [
            product_name,
            *aliases,
            *keywords,
            product_type,
            normalize_text(first.get("name")),
            pricing_basis,
            spec_text,
            condition_text,
            category,
        ]
        search_text = " ".join(dict.fromkeys(part for part in search_parts if part))

        docs.append(
            {
                "id": stable_key("product", logical_id),
                "logical_item_id": logical_id,
                "year": year,
                "category": category,
                "product_name": product_name,
                "product_aliases": aliases,
                "product_type": product_type,
                "keywords": keywords,
                "keywords_text": " ".join(keywords),
                "product_spec_text": spec_text or None,
                "product_condition_text": condition_text or None,
                "pricing_basis": pricing_basis,
                "search_text": search_text,
                "notes_text": note,
                "award_vendors": award_vendors or None,
                "price_min": min(numeric_awards) if numeric_awards else None,
                "price_max": max(numeric_awards) if numeric_awards else None,
                "quantity_min_all": min(qty_mins) if qty_mins else None,
                "quantity_max_all": max(qty_maxs) if qty_maxs else None,
                "tiers": tiers,
            }
        )
    return docs


def print_dry_run(payload: dict[str, Any], documents: list[dict[str, Any]], stats: dict[str, int]) -> None:
    print(f"Source: {payload['source_file']}")
    print(f"Source SHA-256: {payload['source_sha256']}")
    print(f"Rows/items: {stats['items']}")
    print(f"Logical products: {stats['logical_items']}")
    print(f"Missing quantity: {stats['missing_quantity']}")
    print(f"Missing awarded price: {stats['missing_awarded_price']}")
    print(f"Documents prepared: {len(documents)}")
    print(f"Unique document IDs: {len({document['id'] for document in documents})}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--enrichment-file", type=Path, default=DEFAULT_ENRICHMENT)
    parser.add_argument("--index", default=INDEX_NAME)
    parser.add_argument("--dry-run", action="store_true", help="Validate and build documents without Azure changes")
    parser.add_argument(
        "--create-index", action="store_true", help="Delete and recreate only the target index (destructive)"
    )
    parser.add_argument("--enrich", action="store_true", help="Generate missing LLM enrichment records")
    parser.add_argument("--ingest", action="store_true", help="Embed and upload all master rows")
    parser.add_argument("--verify", action="store_true", help="Verify target index count and sample query")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.create_index and args.index != INDEX_NAME:
        raise RuntimeError("--create-index is allowed only for the default target index")
    if args.dry_run and any([args.create_index, args.ingest, args.verify]):
        raise RuntimeError("--dry-run cannot be combined with Azure-changing operations")
    if not any([args.dry_run, args.create_index, args.enrich, args.ingest, args.verify]):
        raise RuntimeError("Choose an operation, for example --dry-run or --create-index --ingest --verify")

    payload = load_master_items(args.master)
    stats = validate_source(payload)
    enrichments = load_enrichment(args.enrichment_file, payload["source_sha256"])

    if args.enrich:
        endpoint = required_env("AZURE_OPENAI_ENDPOINT", "OPENAI_API_BASE_URL")
        key = required_env("AZURE_OPENAI_KEY", "OPENAI_API_KEY")
        deployment = os.environ.get("AZURE_OPENAI_ENRICHMENT_DEPLOYMENT", "deploy-gpt-5.4-mini")
        api_version = os.environ.get(
            "AZURE_OPENAI_API_VERSION",
            os.environ.get("OPENAI_API_VERSION", "2024-10-21"),
        )
        enrichments = generate_enrichment(
            payload["items"],
            enrichments,
            endpoint,
            key,
            api_version,
            deployment,
            checkpoint_path=args.enrichment_file,
            source_sha256=payload["source_sha256"],
        )
        save_enrichment(args.enrichment_file, payload["source_sha256"], enrichments)
        print(f"Wrote enrichment cache: {args.enrichment_file}")

    documents = build_product_documents(payload["items"], enrichments)
    print_dry_run(payload, documents, stats)
    if args.dry_run:
        return 0

    endpoint = required_env("AZURE_SEARCH_ENDPOINT")
    search_key = required_env("AZURE_SEARCH_ADMIN_KEY", "AZURE_SEARCH_KEY")
    api = SearchApi(endpoint, search_key, args.index)

    if args.create_index:
        api.ensure_index(force_recreate=True)
    elif args.ingest:
        api.ensure_index(force_recreate=False)

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
                f"Target index verification failed: HTTP {schema_response.status_code}"
            )
        schema = schema_response.json()
        vector_fields = [
            value for value in schema.get("fields", []) if value.get("name") == "content_vector"
        ]
        if not vector_fields or vector_fields[0].get("dimensions") != EMBEDDING_DIMENSIONS:
            raise RuntimeError(f"Target index content_vector dimensions are not {EMBEDDING_DIMENSIONS}")
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
    except (RuntimeError, Exception) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
