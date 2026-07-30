#!/usr/bin/env python3
"""
Procurement Price Lookup Tool

ใช้สำหรับค้นหาราคาและข้อมูลสินค้า Trade Marketing Materials โดยเรียกใช้
data loader และให้ LLM Agent เรียกใช้ผ่าน function calling
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Add parent to path for imports
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from load_master import load_procurement_data, ProcurementLoader


def lookup_price(
    item_name: str,
    quantity: Optional[int] = None,
    category: Optional[str] = None,
) -> str:
    """
    ค้นหาราคาสินค้าจากชื่อสินค้า พร้อมปริมาณและหมวดหมู่

    Args:
        item_name: ชื่อหรือคำค้นหาสินค้า (เช่น "เสื้อยืด", "ป้ายไวนิล")
        quantity: ปริมาณที่ต้องการ (optional)
        category: หมวดหมู่สินค้า (POSM, Printing, Garment, Premium)

    Returns:
        JSON string ผลลัพธ์ราคาและข้อมูลสินค้า
    """
    try:
        # Load data
        loader = ProcurementLoader(str(ROOT / "data" / "source" / "master-price-template.xlsx"))
        items_df, tiers_df, relations_df = load_procurement_data(loader)

        # Search for item
        results = loader.find_items(item_name, category=category, limit=5)

        if not results:
            return json.dumps({
                "status": "not_found",
                "message": f"ไม่พบสินค้า '{item_name}' ในระบบ",
                "suggestions": "ลองค้นหาด้วยชื่ออื่นหรือตรวจสอบการสะกดคำ"
            }, ensure_ascii=False, indent=2)

        # Process results
        response_items = []
        for item_id, item_row in results:
            item_info = {
                "item_id": item_id,
                "name": item_row.get("item_name", ""),
                "category": item_row.get("category", ""),
                "unit": item_row.get("unit", ""),
                "prices": []
            }

            # Get pricing tiers for this item
            if quantity:
                price_info = loader.lookup_price(item_id, quantity)
                if price_info:
                    item_info["prices"].append({
                        "quantity": quantity,
                        "price_per_unit": float(price_info.get("price_per_unit", 0)),
                        "total_price": float(price_info.get("price_per_unit", 0)) * quantity,
                        "vendor": price_info.get("vendor_name", ""),
                        "tier": price_info.get("qty_tier", "")
                    })
            else:
                # Show all available tiers
                item_tiers = tiers_df[tiers_df["item_id"] == item_id]
                for _, tier in item_tiers.iterrows():
                    item_info["prices"].append({
                        "quantity_range": f"{tier.get('qty_min', 0)}-{tier.get('qty_max', 0)}",
                        "price_per_unit": float(tier.get("price_per_unit", 0)),
                        "vendor": tier.get("vendor_name", "")
                    })

            response_items.append(item_info)

        return json.dumps({
            "status": "success",
            "total_results": len(response_items),
            "items": response_items
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False, indent=2)


def get_item_details(item_id: str) -> str:
    """
    ดูรายละเอียดเต็มของสินค้า (เกี่ยวข้องสินค้า, vendor ทั้งหมด, ราคาทั้งหมด)

    Args:
        item_id: รหัสสินค้า (เช่น "PRT-001")

    Returns:
        JSON string ประกอบด้วยข้อมูลเต็มและรายการสินค้าที่เกี่ยวข้อง
    """
    try:
        loader = ProcurementLoader(str(ROOT / "data" / "source" / "master-price-template.xlsx"))
        items_df, tiers_df, relations_df = load_procurement_data(loader)

        # Get item
        item_row = items_df[items_df["item_id"] == item_id]
        if item_row.empty:
            return json.dumps({
                "status": "not_found",
                "message": f"ไม่พบสินค้า ID '{item_id}'"
            }, ensure_ascii=False, indent=2)

        item_data = item_row.iloc[0].to_dict()

        # Get all price tiers
        item_tiers = tiers_df[tiers_df["item_id"] == item_id]
        prices = []
        for _, tier in item_tiers.iterrows():
            prices.append({
                "qty_tier": f"{tier.get('qty_min', 0)}-{tier.get('qty_max', 0)}",
                "price": float(tier.get("price_per_unit", 0)),
                "vendor": tier.get("vendor_name", "")
            })

        # Get related items
        related_items = relations_df[relations_df["item_id_a"] == item_id]
        relations = []
        for _, rel in related_items.iterrows():
            relations.append({
                "related_item_id": rel.get("item_id_b", ""),
                "relation_type": rel.get("relation_type", ""),
                "description": rel.get("description", "")
            })

        return json.dumps({
            "status": "success",
            "item": {
                "id": item_id,
                "name": item_data.get("item_name", ""),
                "category": item_data.get("category", ""),
                "unit": item_data.get("unit", ""),
                "description": item_data.get("description", "")
            },
            "pricing_tiers": prices,
            "related_items": relations
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False, indent=2)


def list_categories() -> str:
    """รายการหมวดหมู่สินค้าทั้งหมดในระบบ"""
    try:
        loader = ProcurementLoader(str(ROOT / "data" / "source" / "master-price-template.xlsx"))
        items_df, _, _ = load_procurement_data(loader)

        categories = items_df["category"].unique().tolist()
        return json.dumps({
            "status": "success",
            "categories": categories,
            "total": len(categories)
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Test functions
    print("=== Test: lookup_price ===")
    print(lookup_price("เสื้อยืด", quantity=100))
    print("\n=== Test: list_categories ===")
    print(list_categories())
