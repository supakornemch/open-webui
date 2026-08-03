#!/usr/bin/env python3
"""
Generate variants metadata for LLM clarification questions.

Auto-detect patterns from catalog.json and create clarification rules
for products with multiple variants.
"""

import json
from collections import defaultdict
from pathlib import Path

INPUT_FILE = "data/catalog.json"
OUTPUT_FILE = "data/variants_metadata.json"

def analyze_variants(catalog):
    """Group items by base_name and analyze variant dimensions."""
    
    base_groups = defaultdict(list)
    for item in catalog['items']:
        base_groups[item['base_name']].append(item)
    
    # Filter to only multi-variant products
    variants = {k: v for k, v in base_groups.items() if len(v) > 1}
    
    metadata = {}
    
    for base_name, items in variants.items():
        # Collect all spec keys across variants
        all_specs = {}
        for item in items:
            for key, value in item['specs'].items():
                if key not in all_specs:
                    all_specs[key] = set()
                all_specs[key].add(value)
        
        # Build dimensions
        dimensions = {}
        for spec_key, values in all_specs.items():
            if len(values) > 1:  # Only include if there are actual variants
                dimensions[spec_key] = {
                    'type': 'single_choice',
                    'options': sorted(list(values)),
                    'required': True,
                    'question': generate_question(spec_key, values)
                }
        
        if dimensions:
            metadata[base_name] = {
                'base_name': base_name,
                'variant_type': 'DISCRETE_OPTIONS',
                'variant_count': len(items),
                'dimensions': dimensions,
                'items': [
                    {
                        'item_id': item['item_id'],
                        'specs': item['specs'],
                        'price': item['winner_price']
                    }
                    for item in items
                ]
            }
    
    return metadata

def generate_question(spec_key, values):
    """Generate Thai clarification question based on spec key."""
    
    questions = {
        'ขนาด': 'ต้องการขนาดไหนครับ?',
        'โครง': 'ต้องการโครงแบบไหน?',
        'สี': 'ต้องการสีแบบไหน?',
        'ผ้า': 'ต้องการผ้าแบบไหน?',
        'วัสดุ': 'ต้องการวัสดุอะไร?',
        'ชนิด': 'ต้องการชนิดไหน?'
    }
    
    if spec_key in questions:
        return questions[spec_key]
    
    # Default question
    values_list = ', '.join(list(values)[:3])
    return f'ต้องการ{spec_key}แบบไหน? (เช่น {values_list})'

def create_manual_entries():
    """Create manual metadata entries for items not in Excel but mentioned in requirements."""
    
    manual = {
        'ธงปีกนก': {
            'base_name': 'ธงปีกนก',
            'variant_type': 'OPTIONAL_ADDON',
            'dimensions': {
                'ฐาน': {
                    'type': 'yes_no',
                    'required': True,
                    'question': 'ต้องการฐานด้วยหรือไม่?',
                    'price_impact': 'separate_item'
                }
            },
            'note': 'ฐานเป็นรายการแยกต่างหาก ต้องหาในรายการ "ฐานธงปีกนก"'
        }
    }
    
    return manual

def main():
    print("=== Generating Variants Metadata ===\n")
    
    # Load catalog
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    print(f"Analyzing {len(catalog['items'])} items...")
    
    # Auto-detect variants
    metadata = analyze_variants(catalog)
    
    print(f"\nFound {len(metadata)} products with variants:")
    for base_name, meta in metadata.items():
        dims = ', '.join(meta['dimensions'].keys())
        print(f"  • {base_name}: {meta['variant_count']} variants ({dims})")
    
    # Add manual entries
    manual = create_manual_entries()
    metadata.update(manual)
    
    # Create output
    output = {
        'variants': metadata,
        'metadata': {
            'total_variants': len(metadata),
            'auto_detected': len(metadata) - len(manual),
            'manual_entries': len(manual),
            'generated_at': catalog['metadata']['extracted_at']
        }
    }
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Generated metadata for {len(metadata)} products")
    print(f"📁 Saved to: {OUTPUT_FILE}")
    
    # Show sample
    print("\n=== SAMPLE METADATA ===\n")
    sample_name = 'ร่มโค้ก 36 นิ้ว'
    if sample_name in metadata:
        sample = metadata[sample_name]
        print(f"Product: {sample_name}")
        print(f"Variants: {sample['variant_count']}")
        print(f"Dimensions:")
        for dim_name, dim_spec in sample['dimensions'].items():
            print(f"  • {dim_name}:")
            print(f"    Options: {dim_spec['options']}")
            print(f"    Question: {dim_spec['question']}")

if __name__ == '__main__':
    main()
