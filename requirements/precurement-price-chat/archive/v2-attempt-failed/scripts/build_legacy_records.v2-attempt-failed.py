#!/usr/bin/env python3
"""Build Azure AI Search records from the legacy Trade Marketing Materials Excel.

The legacy workbook has a different structure: each category is a separate sheet
with vendor price columns and a single winner price column. This parser reads
awarded prices directly from the ``ราคาที่ผ่านการประมูล`` column.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "Trade Marketing Materials price for Y2026.final.xlsx"
DEFAULT_OUTPUT = ROOT / "procurement_legacy_prices_for_search.jsonl"

SHEET_CONFIG = (
    ("POSM(MKT)", "1.POSM(MKT)", 1),
    ("Printing(MKT)", "2.Printing(MKT)", 1),
    ("Garment", "3.Garment", 1),
    ("Premium", "4.สรุปPremium", 1),
    ("Printing-Rate", "5.Printing-Rate1-43", 1),
    ("Printing-Rate", "5.Printing-Rate44-109", 4),
)

SOURCE_VENDOR_FIELDS = tuple(f"source_vendor_{number}" for number in range(1, 16))


def compact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")


def display(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value).strip()


def quantity_label(value: Any) -> str:
    return display(value)


def number(value: Any) -> float | None:
    text = display(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def quantity_bounds(value: Any) -> tuple[int | None, int | None]:
    text = quantity_label(value).replace(",", "")
    numbers = [int(number_text) for number_text in re.findall(r"\d+", text)]
    if not numbers:
        return None, None
    if len(numbers) >= 2 and re.search(r"[-–—ถึง]|\bto\b", text, re.IGNORECASE):
        lower, upper = numbers[0], numbers[1]
        return (lower, upper) if lower <= upper else (None, None)
    return numbers[0], None


def exact_column(columns: list[Any], *names: str) -> Any | None:
    wanted = {name.strip().casefold() for name in names}
    for column in columns:
        if display(column).casefold() in wanted:
            return column
    return None


def history_columns(columns: list[Any], year: int) -> tuple[Any | None, Any | None]:
    label = f"History {year}".casefold()
    for position, column in enumerate(columns):
        if display(column).casefold() == label:
            next_column = columns[position + 1] if position + 1 < len(columns) else None
            return column, next_column
    return None, None


def source_row_json(row: pd.Series) -> str:
    values: dict[str, str] = {}
    seen: dict[str, int] = {}
    for position, column in enumerate(row.index):
        raw_key = display(column)
        key = re.sub(r"[^A-Za-z0-9]+", "_", raw_key).strip("_").lower()
        if not key or key.startswith("unnamed"):
            key = f"column_{position + 1}"
        count = seen.get(key, 0)
        seen[key] = count + 1
        if count:
            key = f"{key}_{count + 1}"
        values[key] = display(row.iloc[position])
    return json.dumps(values, ensure_ascii=False)


def vendor_columns(columns: list[Any]) -> dict[int, Any]:
    result = {}
    for column in columns:
        match = re.fullmatch(r"vendor\s*(\d+)", display(column), re.IGNORECASE)
        if match:
            result[int(match.group(1))] = column
    return result


def build_records(source: Path) -> tuple[list[dict[str, Any]], list[str]]:
    xl = pd.ExcelFile(source)
    records = []
    warnings = []

    for category, sheet_name, header_row in SHEET_CONFIG:
        if sheet_name not in xl.sheet_names:
            warnings.append(f"Sheet {sheet_name} not found")
            continue

        df = pd.read_excel(source, sheet_name=sheet_name, header=header_row)
        columns = list(df.columns)
        item_col = exact_column(columns, "Item", "ลำดับ")
        desc_col = exact_column(columns, "รายการ", "รายากร")
        source_qty_col = exact_column(columns, "QTY")
        source_qty_y2026_col = exact_column(columns, "QTY Y2026")
        qty_col = source_qty_y2026_col or source_qty_col
        source_qty_y2025_col = exact_column(columns, "QTY Y2025")
        source_price_y2025_col = exact_column(columns, "Price Y2025")
        source_supplier_2025_col = exact_column(columns, "Supplier 2025")
        price_col = exact_column(columns, "ราคาที่ผ่านการประมูล")
        award_vendor_cols = [
            column
            for column in columns
            if display(column).casefold().startswith("รายชื่อผู้ผ่านการประมูล")
        ]
        vendor_col = award_vendor_cols[0] if award_vendor_cols else None
        source_vendors = vendor_columns(columns)
        history = {
            year: history_columns(columns, year)
            for year in (2023, 2024, 2025)
        }

        if not all([item_col, desc_col, price_col]):
            warnings.append(f"Sheet {sheet_name} missing required columns")
            continue

        current_item = ""
        current_description = ""
        for idx, row in df.iterrows():
            raw_item = display(row[item_col])
            raw_description = display(row[desc_col])
            if raw_item:
                current_item = raw_item
            if raw_description:
                current_description = raw_description
            item_number = current_item
            description = current_description
            price = number(row[price_col])
            vendor = display(row[vendor_col]) if vendor_col else ""
            qty = quantity_label(row[qty_col]) if qty_col else ""
            source_row = idx + header_row + 2

            if not item_number or not description:
                continue

            if price is None or price <= 0:
                continue

            qty_min, qty_max = quantity_bounds(qty)
            history_values = {}
            for year, (qty_column, price_column) in history.items():
                history_values[f"source_history_{year}_qty"] = (
                    display(row[qty_column]) if qty_column else ""
                )
                history_values[f"source_history_{year}_price"] = (
                    display(row[price_column]) if price_column else ""
                )
            source_values = {
                "source_workbook": source.name,
                "source_sheet": sheet_name,
                "source_header_row": header_row + 1,
                "source_row": source_row,
                "source_category": category,
                "source_item": item_number,
                "source_description": description,
                "source_qty": display(row[source_qty_col]) if source_qty_col else "",
                "source_qty_y2025": display(row[source_qty_y2025_col]) if source_qty_y2025_col else "",
                "source_price_y2025": display(row[source_price_y2025_col]) if source_price_y2025_col else "",
                "source_supplier_2025": display(row[source_supplier_2025_col]) if source_supplier_2025_col else "",
                "source_qty_y2026": display(row[source_qty_y2026_col]) if source_qty_y2026_col else "",
                "source_awarded_price": price,
                "source_awarded_vendor": vendor,
                "source_award_notes": " | ".join(
                    display(row[column]) for column in award_vendor_cols[1:] if display(row[column])
                ),
                "source_row_json": source_row_json(row),
            }
            source_values.update(history_values)
            for vendor_number in range(1, 16):
                column = source_vendors.get(vendor_number)
                source_values[f"source_vendor_{vendor_number}"] = (
                    display(row[column]) if column else ""
                )

            record_id = compact_id(f"{category}_{sheet_name}_{item_number}_{qty}_{source_row}")
            record = {
                "id": record_id,
                "product_code": f"{compact_id(category)}-{item_number}",
                "product_name": description,
                "category": category,
                "pricing_model": "ต่อชิ้น",
                "variant_code": "",
                "variant_description": "",
                "vendor_code": "",
                "vendor_name": vendor,
                "year": 2026,
                "price": price,
                "qty": qty,
                "qty_min": qty_min,
                "qty_max": qty_max,
                "notes": source_values["source_award_notes"],
                "product_description": description,
                "related_products": [],
                "corpus": "procurement-legacy-prices",
                "source": source.name,
            }
            record.update(source_values)
            record["content"] = (
                f"{description} | {record['product_code']} | หมวด {category} | "
                f"ราคา {price:g} บาท | จำนวน {qty} | ผู้ขาย {vendor} | ปี 2026 | "
                + " ".join(
                    f"vendor {vendor_number} {record[f'source_vendor_{vendor_number}']}"
                    for vendor_number in range(1, 16)
                    if record[f"source_vendor_{vendor_number}"]
                )
            )
            records.append(record)

    if not records:
        raise ValueError("No records found in any category sheet")

    return records, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Build legacy procurement records for Azure AI Search")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.source.exists():
        raise FileNotFoundError(f"Source file not found: {args.source}")

    records, warnings = build_records(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    with args.output.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    categories = sorted({record["category"] for record in records})
    print(f"Wrote {len(records)} legacy price record(s) to {args.output}")
    print(f"Categories: {', '.join(categories)}")
    for warning in warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
