#!/usr/bin/env python3
"""
Regression test runner for procurement_price_lookup tool.

Reads regression-tests.csv and validates search behavior against local JSON data.
Does NOT call OWUI API — tests the matching logic directly.

Usage:
    python run_regression.py              # run all tests
    python run_regression.py --verbose    # show details per test
    python run_regression.py --csv        # output results as CSV
"""

import csv
import json
import re
import sys
from pathlib import Path

JSON_DIR = Path(__file__).resolve().parents[1] / "data" / "generated" / "json"
CSV_PATH = Path(__file__).parent / "regression-tests.csv"

# ── Replicate tool logic ────────────────────────────────────────────

SYNONYMS = {
    "โฟมบอร์ด": "pp board", "ไดคัด": "ไดคัท", "มิล": "mm",
    "โค้ก": "โคคา-โคล่า", "ปริ้นท์": "พิมพ์", "ปรินท์": "พิมพ์",
    "ล้อมกอง": "wrap around", "ป้ายล้อมกอง": "wrap around",
    "เกียรติบัตร": "ประกาศนียบัตร", "เกียรติ": "ประกาศนียบัตร",
    "certificate": "ประกาศนียบัตร",
}

NOISE = {"for","and","the","with","pdf","file","2026","y2026",
         "การ","จะ","ให้","ด้วย","เพื่อ","อย่าง","เป็น","ที่","มี"}


def expand_synonyms(text):
    t = text.lower()
    for u, d in SYNONYMS.items():
        if u in t and d not in t:
            t += " " + d
    return t


def tokenize(text):
    text = expand_synonyms(text)
    raw = re.split(r'[\s,/.()\-]+', text.lower())
    tokens = []
    for t in raw:
        if len(t) < 2 or t in NOISE:
            continue
        tokens.append(t)
        m = re.match(r'^(\d+)\s*[x×]\s*(\d+)$', t)
        if m:
            a, b = m.group(1), m.group(2)
            if a not in tokens: tokens.append(a)
            if b not in tokens: tokens.append(b)
            nums = sorted([a, b], key=int)
            sd = f"{nums[0]}x{nums[1]}"
            if sd != t and sd not in tokens:
                tokens.append(sd)
    return tokens


def is_dim_token(t):
    if re.match(r'^\d+\s*[x×]\s*\d+$', t):
        return True
    if t.isdigit() and 2 <= len(t) <= 5:
        return True
    return False


def match_score(query, item_name):
    q_tokens = tokenize(query)
    n_tokens = tokenize(item_name)
    if not q_tokens:
        return 0.0

    q_dims = [t for t in q_tokens if is_dim_token(t)]
    n_dims = [t for t in n_tokens if is_dim_token(t)]
    q_text = [t for t in q_tokens if t not in q_dims]
    n_text = [t for t in n_tokens if t not in n_dims]

    matched_text = 0.0
    for qt in q_text:
        best = 0.0
        for nt in n_text:
            if qt == nt:
                best = 1.0; break
            elif qt in nt:
                best = max(best, len(qt) / len(nt))
            elif nt in qt and len(nt) >= 3:
                best = max(best, len(nt) / len(qt))
        matched_text += best

    dim_score = 1.0
    if q_dims:
        q_set = set(q_dims)
        n_set = set(n_dims)
        if n_set:
            dim_score = len(q_set & n_set) / max(len(q_set), 1)
        else:
            dim_score = 0.0

    text_score = matched_text / max(len(q_text), 1) if q_text else 0.0
    if query.lower() in item_name.lower():
        text_score = max(text_score, 1.0)

    return 0.7 * text_score + 0.3 * dim_score


def search(query, top=3):
    """Search all items, return top matches."""
    results = []
    for fn, items in ALL_ITEMS:
        for item in items:
            name = item.get("item_name", item.get("n", ""))
            score = match_score(query, name)
            if score >= 0.35:  # MIN_SCORE threshold
                price = item.get("approved_price_per_unit", item.get("p", 0))
                results.append((score, fn, name, price))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top]


# ── Load data ───────────────────────────────────────────────────────

ALL_ITEMS = []
for fn in ["1.POSM(MKT).json", "2.Printing(MKT).json", "3.Garment.json",
           "4.สรุปPremium.json", "5.Printing-Rate.json"]:
    path = JSON_DIR / fn
    if not path.exists():
        print(f"WARNING: {path} not found")
        continue
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ALL_ITEMS.append((fn, data))


# ── Run tests ───────────────────────────────────────────────────────

def run_tests(verbose=False):
    passed = 0
    failed = 0
    skipped = 0

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tests = list(reader)

    results = []

    for t in tests:
        tid = t["id"]
        query = t["query"]
        expected_item = t["expected_item"]
        expected_price = t["expected_price"]
        scenario = t["scenario"]
        notes = t.get("notes", "")

        # Skip meta/behavioral tests
        if tid.startswith("EDGE-") and "VAT" in scenario or "Lead time" in scenario or "No assume" in scenario:
            if verbose:
                print(f"  ⏭  {tid}: {scenario} (behavioral — test manually)")
            skipped += 1
            results.append({"id": tid, "status": "SKIP", "scenario": scenario, "query": query,
                           "expected": expected_item, "actual": "N/A (behavioral)", "score": "-"})
            continue

        if tid.startswith("META-"):
            if verbose:
                print(f"  ⏭  {tid}: {scenario} (API test — run manually)")
            skipped += 1
            results.append({"id": tid, "status": "SKIP", "scenario": scenario, "query": query,
                           "expected": expected_item, "actual": "N/A (API)", "score": "-"})
            continue

        # Run search
        matches = search(query, top=3)

        if not matches:
            if expected_item in ("not found", "no result"):
                if verbose: print(f"  ✅ {tid}: {scenario} → not found (expected)")
                passed += 1
                results.append({"id": tid, "status": "PASS", "scenario": scenario, "query": query,
                               "expected": "not found", "actual": "not found", "score": "-"})
            else:
                if verbose: print(f"  ❌ {tid}: {scenario} → not found (expected: {expected_item[:50]})")
                failed += 1
                results.append({"id": tid, "status": "FAIL", "scenario": scenario, "query": query,
                               "expected": expected_item[:50], "actual": "not found", "score": "0"})
            continue

        top_match = matches[0]
        score, fn, name, price = top_match

        # Check if item matches expectation
        item_ok = any(kw.lower() in name.lower() for kw in expected_item.lower().split())
        price_ok = True
        if expected_price and expected_price not in ("not found", "found", "any", "N/A"):
            try:
                expected_val = float(expected_price.split()[0].replace(",", ""))
                if expected_item.startswith("must"):
                    price_ok = price > 0  # just check it found something
                else:
                    price_ok = abs(price - expected_val) < max(expected_val * 0.3, 5)
            except ValueError:
                price_ok = True

        passed_this = item_ok and price_ok
        status = "PASS" if passed_this else "FAIL"

        if passed_this:
            passed += 1
            if verbose: print(f"  ✅ {tid}: {scenario} → {name[:60]} ({score:.0%}, {price} THB)")
        else:
            failed += 1
            if verbose:
                print(f"  ❌ {tid}: {scenario}")
                print(f"     expected: {expected_item[:80]}")
                print(f"     got:      {name[:80]} ({score:.0%}, {price} THB)")

        results.append({
            "id": tid, "status": status, "scenario": scenario, "query": query,
            "expected": expected_item[:60], "actual": f"{name[:60]} ({score:.0%}, {price} THB)", "score": f"{score:.0%}"
        })

    return results, passed, failed, skipped


def main():
    verbose = "--verbose" in sys.argv
    csv_out = "--csv" in sys.argv

    print(f"🔄 Running {sum(1 for _ in open(CSV_PATH)) - 1} regression tests...\n")

    results, passed, failed, skipped = run_tests(verbose=verbose)

    total = passed + failed + skipped
    print(f"\n{'='*60}")
    print(f"Results: {passed} ✅ | {failed} ❌ | {skipped} ⏭  | {total} total")
    print(f"{'='*60}")

    if csv_out:
        writer = csv.DictWriter(sys.stdout, fieldnames=["id","status","scenario","query","expected","actual","score"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
