#!/usr/bin/env python3
"""Build Azure AI Search records from the normalized Procurement template v2.

The source workbook is relational: product, variant, vendor, and vendor price
data live in separate sheets. This exporter joins those sheets itself because
Python readers do not recalculate Excel VLOOKUP formulas.

All rows in ``Vendor_Prices`` are emitted when their product, variant, vendor,
price, and quantity data are valid. The single ``Qty`` column may contain a
flat minimum (``1``), a range (``1-99 ชิ้น``), or an open-ended tier
(``500+ ชิ้น``). A blank year remains null in the index.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "scripts/Procurement_Price_Template_v2.xlsx"
DEFAULT_OUTPUT = ROOT / "procurement_prices_for_search.jsonl"
REQUIRED_SHEETS = {"Products", "Variants", "Vendors", "Vendor_Prices"}
REQUIRED_PRICE_COLUMNS = {
    "Product Code",
    "Variant Code",
    "Vendor Code",
    "Price",
    "Qty",
    "Year",
    "Notes",
}


def read_rows(workbook: Any, sheet_name: str) -> list[dict[str, Any]]:
    sheet = workbook[sheet_name]
    headers = [str(cell.value or "").strip() for cell in next(sheet.iter_rows(max_row=1))]
    rows = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if not any(value is not None and str(value).strip() for value in values):
            continue
        rows.append({header: values[index] if index < len(values) else None for index, header in enumerate(headers)})
    return rows


def compact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")


def display(value: Any) -> str:
    return "" if value is None else str(value).strip()


def quantity_bounds(value: Any) -> tuple[int, int | None]:
    """Convert the single Qty field into inclusive minimum and maximum bounds."""
    text = display(value).replace(",", "")
    numbers = [int(number) for number in re.findall(r"\d+", text)]
    if not numbers:
        raise ValueError(f"Invalid Qty: {value!r}")
    if len(numbers) >= 2 and re.search(r"[-–—ถึง]|\bto\b", text, re.IGNORECASE):
        lower, upper = numbers[0], numbers[1]
        if lower > upper:
            raise ValueError(f"Invalid Qty range: {value!r}")
        return lower, upper
    return numbers[0], None


def related_products(product: dict[str, Any], quote: dict[str, Any]) -> list[str]:
    """Read declared follow-up items from the product or quote metadata.

    Prefer the structured ``Related Products Code`` column. A source workbook may
    also use the strict Notes convention ``RELATED_PRODUCTS: item A; item B``.
    Free-form notes are intentionally ignored so the assistant never invents
    an accessory relationship from prose.
    """
    values = [display(product.get("Related Products Code"))]
    notes = display(quote.get("Notes")) or display(product.get("Notes"))
    match = re.search(r"\bRELATED_PRODUCTS?\s*:\s*([^\r\n]+)", notes, re.IGNORECASE)
    if match:
        values.append(match.group(1))

    items = []
    for value in values:
        for item in re.split(r"[;|\r\n]+", value):
            item = item.strip()
            if item and item not in items:
                items.append(item)
    return items


def build_records(source: Path) -> tuple[list[dict[str, Any]], list[str]]:
    workbook = load_workbook(source, read_only=True, data_only=True)
    missing_sheets = REQUIRED_SHEETS - set(workbook.sheetnames)
    if missing_sheets:
        raise ValueError(f"Missing sheets: {', '.join(sorted(missing_sheets))}")

    products = read_rows(workbook, "Products")
    variants = read_rows(workbook, "Variants")
    vendors = read_rows(workbook, "Vendors")
    prices = read_rows(workbook, "Vendor_Prices")
    workbook.close()

    price_columns = set(prices[0]) if prices else set()
    missing_columns = REQUIRED_PRICE_COLUMNS - price_columns
    if missing_columns:
        raise ValueError(
            "Vendor_Prices is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    product_by_code = {display(row["Product Code"]): row for row in products}
    variant_by_code = {display(row["Variant Code"]): row for row in variants}
    vendor_by_code = {display(row["Vendor Code"]): row for row in vendors}
    records = []
    missing_references = []

    for row in prices:
        product_code = display(row["Product Code"])
        variant_code = display(row["Variant Code"])
        vendor_code = display(row["Vendor Code"])
        product = product_by_code.get(product_code)
        variant = variant_by_code.get(variant_code) if variant_code else None
        vendor = vendor_by_code.get(vendor_code)
        if not product or not vendor or (variant_code and not variant):
            missing_references.append(
                f"product={product_code!r}, variant={variant_code!r}, vendor={vendor_code!r}"
            )
            continue

        price = row["Price"]
        if not isinstance(price, (int, float)) or price < 0:
            raise ValueError(f"Invalid Price for product {product_code}: {price!r}")

        item_name = display(product.get("Product Name"))
        variant_description = display(variant.get("Description")) if variant else ""
        vendor_name = display(vendor.get("Vendor Name"))
        year = int(row["Year"]) if row["Year"] is not None else None
        related = related_products(product, row)
        quantity = str(row["Qty"]) if row["Qty"] is not None else ""
        try:
            qty_min, qty_max = quantity_bounds(quantity)
        except ValueError as error:
            missing_references.append(f"product={product_code!r}: {error}")
            continue
        source_key = "|".join(
            (product_code, variant_code or "base", vendor_code, str(year or "unknown"), quantity)
        )
        record = {
            "id": compact_id(source_key),
            "product_code": product_code,
            "product_name": item_name,
            "category": display(product.get("Category")),
            "pricing_model": display(product.get("Pricing Model")),
            "variant_code": variant_code,
            "variant_description": variant_description,
            "vendor_code": vendor_code,
            "vendor_name": vendor_name,
            "year": year,
            "price": float(price),
            "qty": quantity,
            "qty_min": qty_min,
            "qty_max": qty_max,
            "notes": display(row["Notes"]),
            "product_description": display(row.get("Product Description", "")),
            "related_products": related,
            "corpus": "procurement-prices",
            "source": source.name,
        }
        product_text = " ".join(
            part for part in (product_code, item_name, variant_code, variant_description,
                              display(row.get("Product Description", ""))) if part
        )
        related_text = f" | ต้องค้นหาราคาต่อ: {', '.join(related)}" if related else ""
        record["content"] = (
            f"{product_text} | หมวด {record['category']} | ราคา {record['price']:g} บาท "
            f"| จำนวน {record['qty']} | ผู้ขาย {vendor_name} | ปี {year or 'ไม่ระบุ'}{related_text}"
        )
        records.append(record)

    if missing_references:
        print(f"Warning: Skipped {len(missing_references)} row(s) with incomplete data:")
        for ref in missing_references[:5]:
            print(f"  {ref}")
    if not records:
        raise ValueError("No records found in Vendor_Prices sheet")

    warnings = []
    if missing_references:
        warnings.append(f"Skipped {len(missing_references)} row(s) with incomplete data")
    return records, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Procurement v2 Azure AI Search records")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records, warnings = build_records(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    categories = sorted({record["category"] for record in records})
    print(f"Wrote {len(records)} awarded price record(s) to {args.output}")
    print(f"Categories: {', '.join(categories)}")
    for warning in warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()