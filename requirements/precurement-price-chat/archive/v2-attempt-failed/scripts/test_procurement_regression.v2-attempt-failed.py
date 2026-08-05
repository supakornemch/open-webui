#!/usr/bin/env python3
"""Regression tests for Procurement Template v2 in Azure AI Search.

The test uses the same hybrid retrieval shape as ``procurement-search.py`` and
asserts the business contract: only awarded, specification-compliant quotes are
available to the assistant. It covers representative Thai and English queries
across POSM, Printing, Garment, and Premium.

Usage:
  set -a && source docker/.env.owui && set +a
  python3 requirements/precurement-price-chat/scripts/test_procurement_regression.py
"""

import json
import os
import sys
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import requests


INDEX_NAME = "procurement-prices-th-idx"
SEARCH_API_VERSION = "2024-07-01"
OPENAI_API_VERSION = "2024-10-21"
EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
MAX_RESULTS = 10
BUILD_RECORDS_PATH = Path(__file__).with_name("build_search_records.py")


@dataclass(frozen=True)
class Scenario:
    name: str
    query: str
    expected_id: str
    expected_price: float
    expected_category: str


SCENARIOS = [
    Scenario("POSM umbrella, steel, fixed color", "ร่มโค้ก 36 นิ้ว โครงเหล็ก สีตาย", "POSM-001_POSM-001-V1_VEN-A_2026", 523.0, "POSM"),
    Scenario("POSM tissue box", "กล่องทิชชูโค้ก", "POSM-002_base_VEN-C_2026", 28.5, "POSM"),
    Scenario("POSM apron, half", "ผ้ากันเปื้อนโคคาโคล่า ครึ่งตัว", "POSM-003_POSM-003-V2_VEN-E_2026", 55.0, "POSM"),
    Scenario("POSM rack, TT-DSD", "Mega Rack 120x40x150 TT DSD", "POSM-006_POSM-006-V1_VEN-N_2026", 3500.0, "POSM"),
    Scenario("Printing PP Board", "PP Board 85x190 ป้ายหน้าเคาน์เตอร์", "PRINT-001_PRINT-001-V2_VEN-F_2026", 450.0, "Printing"),
    Scenario("Printing menu sign", "ป้ายรายการอาหารโค้ก", "PRINT-002_base_VEN-G_2026", 350.0, "Printing"),
    Scenario("Printing rigid board", "แผ่นริจิโค้ก 24x32 นิ้ว", "PRINT-005_PRINT-005-V2_VEN-H_2026", 60.0, "Printing"),
    Scenario("Garment T-shirt, dark", "เสื้อยืด สีเข้ม", "GARMT-001_GARMT-001-V4_VEN-I_2026", 110.0, "Garment"),
    Scenario("Garment polo, mid color", "เสื้อโปโล TC ผ้า TC สีกลาง", "GARMT-002_GARMT-002-V3_VEN-J_2026", 130.0, "Garment"),
    Scenario("Garment screen, four colors", "สกรีน 4 สี", "GARMT-004_GARMT-004-V4_VEN-K_2026", 40.0, "Garment"),
    Scenario("Premium paper cup", "แก้วกระดาษ 22 ออนซ์", "PREM-001_PREM-001-V2_VEN-L_2026", 3.94, "Premium"),
    Scenario("Premium Bean Bag fabric", "Bean Bag วัสดุผ้า", "PREM-004_PREM-004-V2_VEN-M_2026", 800.0, "Premium"),
]

PASS = 0
FAIL = 0


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name}")
    return value


def check(name: str, passed: bool, detail: str = "") -> None:
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}: {detail}")


class ProcurementSearch:
    def __init__(self) -> None:
        self.search_endpoint = required("AZURE_SEARCH_ENDPOINT").rstrip("/")
        self.search_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY") or required("AZURE_SEARCH_KEY")
        self.openai_endpoint = required("OPENAI_API_BASE_URL").rstrip("/")
        self.openai_key = required("OPENAI_API_KEY")
        self.openai_api_version = os.environ.get("OPENAI_API_VERSION", OPENAI_API_VERSION)
        self.search_headers = {"api-key": self.search_key, "Content-Type": "application/json"}
        self.openai_headers = {"api-key": self.openai_key, "Content-Type": "application/json"}
        self.search_url = (
            f"{self.search_endpoint}/indexes/{INDEX_NAME}/docs/search?api-version={SEARCH_API_VERSION}"
        )
        self.embedding_url = (
            f"{self.openai_endpoint}/openai/deployments/{EMBEDDING_DEPLOYMENT}/embeddings"
            f"?api-version={self.openai_api_version}"
        )

    def embedding(self, query: str) -> list[float]:
        response = requests.post(
            self.embedding_url,
            headers=self.openai_headers,
            json={"input": [query], "dimensions": EMBEDDING_DIMENSIONS},
            timeout=60,
        )
        response.raise_for_status()
        vector = response.json()["data"][0]["embedding"]
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(f"Expected embedding dimension {EMBEDDING_DIMENSIONS}, got {len(vector)}")
        return vector

    def search(self, query: str, *, filter_expression: str, top: int = MAX_RESULTS) -> list[dict]:
        response = requests.post(
            self.search_url,
            headers=self.search_headers,
            json={
                "search": query,
                "searchFields": "product_name,variant_description,content",
                "filter": filter_expression,
                "top": top,
                "select": (
                    "id,product_code,product_name,variant_description,category,"
                    "vendor_code,vendor_name,year,price,unit,qty,qty_range,"
                    "is_winner,meets_spec,related_products,corpus,source"
                ),
                "vectorQueries": [
                    {
                        "kind": "vector",
                        "vector": self.embedding(query),
                        "fields": "content_vector",
                        "k": 50,
                    }
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json().get("value", [])

    def all_procurement_records(self) -> list[dict]:
        response = requests.post(
            self.search_url,
            headers=self.search_headers,
            json={
                "search": "*",
                "filter": "corpus eq 'procurement-prices'",
                "top": 1000,
                "count": True,
                "select": "id,category,price,is_winner,meets_spec,related_products,corpus,source",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("value", [])


def test_data_contract(search: ProcurementSearch) -> None:
    print("\n-- Data contract --")
    records = search.all_procurement_records()
    check("exactly 27 awarded records are indexed", len(records) == 27, f"got {len(records)}")
    check("every record is winner and spec-compliant", all(
        record.get("is_winner") is True and record.get("meets_spec") is True
        for record in records
    ))
    check("all four procurement categories are represented", {
        record.get("category") for record in records
    } == {"POSM", "Printing", "Garment", "Premium"})
    check("every record identifies its source workbook", all(record.get("source") for record in records))
    check("every record exposes related-products metadata", all(
        isinstance(record.get("related_products"), list) for record in records
    ))


def test_related_product_metadata() -> None:
    print("\n-- Related product metadata --")
    spec = spec_from_file_location("build_search_records", BUILD_RECORDS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BUILD_RECORDS_PATH}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    check("Related Products column supports multiple items", module.related_products(
        {"Related Products": "ฐานธงปีกนก; กระเป๋าธง"}, {"Notes": ""}
    ) == ["ฐานธงปีกนก", "กระเป๋าธง"])
    check("strict Notes convention supports related item", module.related_products(
        {"Related Products": ""}, {"Notes": "RELATED_PRODUCTS: ฐานธงปีกนก"}
    ) == ["ฐานธงปีกนก"])
    check("free-form notes do not invent an accessory", module.related_products(
        {"Related Products": ""}, {"Notes": "ใช้พร้อมฐานธงปีกนก"}
    ) == [])


def test_product_queries(search: ProcurementSearch) -> None:
    print("\n-- Product queries --")
    approved_filter = "corpus eq 'procurement-prices' and is_winner eq true and meets_spec eq true"
    for scenario in SCENARIOS:
        results = search.search(scenario.query, filter_expression=approved_filter)
        target_position = next(
            (position for position, item in enumerate(results, start=1) if item.get("id") == scenario.expected_id),
            None,
        )
        check(scenario.name + " retrieves the expected variant", target_position is not None,
              f"expected {scenario.expected_id}; got {[item.get('id') for item in results]}")
        if target_position is None:
            continue
        target = next(item for item in results if item.get("id") == scenario.expected_id)
        check(scenario.name + " returns the expected price", target.get("price") == scenario.expected_price,
              f"got {target.get('price')}, expected {scenario.expected_price}")
        check(scenario.name + " returns the expected category", target.get("category") == scenario.expected_category,
              f"got {target.get('category')}, expected {scenario.expected_category}")
        check(scenario.name + " keeps winner/spec controls", target.get("is_winner") is True and target.get("meets_spec") is True)
        print(f"    target rank: {target_position}/{len(results)}")


def test_filters(search: ProcurementSearch) -> None:
    print("\n-- Filter behavior --")
    scenarios = [
        ("POSM category", "ร่มโค้ก", "category eq 'POSM'", lambda item: item.get("category") == "POSM"),
        ("Printing price ceiling", "PP Board", "price le 500", lambda item: item.get("price", 0) <= 500),
        ("Garment price floor", "เสื้อ", "category eq 'Garment' and price ge 100", lambda item: item.get("category") == "Garment" and item.get("price", 0) >= 100),
        ("2026 records", "แก้วกระดาษ", "year eq 2026", lambda item: item.get("year") == 2026),
    ]
    for name, query, extra_filter, predicate in scenarios:
        filter_expression = (
            "corpus eq 'procurement-prices' and is_winner eq true and meets_spec eq true and "
            + extra_filter
        )
        results = search.search(query, filter_expression=filter_expression)
        check(name + " returns result(s)", bool(results))
        check(name + " is enforced for every result", bool(results) and all(predicate(item) for item in results),
              f"got {json.dumps(results, ensure_ascii=False)}")


def main() -> int:
    print("=" * 72)
    print("PROCUREMENT TEMPLATE V2 REGRESSION TESTS")
    print("=" * 72)
    try:
        search = ProcurementSearch()
        test_related_product_metadata()
        test_data_contract(search)
        test_product_queries(search)
        test_filters(search)
    except (RuntimeError, requests.RequestException, KeyError, ValueError) as error:
        print(f"\nERROR: {error}")
        return 1

    print(f"\nRESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())