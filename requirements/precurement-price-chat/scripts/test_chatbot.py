#!/usr/bin/env python3
"""
Test the LLM chatbot flow with sample queries.

Simulates the agent behavior:
1. Parse user query
2. Search catalog
3. Check if clarification needed
4. Return price information
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path

# Get script directory and construct paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'

# Load data
print(f"[DEBUG] Loading from: {DATA_DIR.resolve()}")
with open(DATA_DIR / 'catalog.json', 'r', encoding='utf-8') as f:
    CATALOG = json.load(f)
print(f"[DEBUG] Loaded {len(CATALOG['items'])} items")

with open(DATA_DIR / 'variants_metadata.json', 'r', encoding='utf-8') as f:
    VARIANTS = json.load(f)['variants']


def search_products(query: str) -> List[Dict]:
    """Search products by name (fuzzy matching for Thai text)."""
    results = []
    
    # Split query into keywords (ignore short words)
    keywords = [w for w in query.split() if len(w) > 1]
    
    print(f"[DEBUG] Searching for keywords: {keywords}")
    
    for item in CATALOG['items']:
        # Check if all keywords present in base_name or full_name
        text = f"{item['base_name']} {item['full_name']}"
        
        match_count = sum(1 for kw in keywords if kw in text)
        
        # Match if at least 1 significant keyword found
        if match_count > 0:
            results.append({
                **item,
                '_match_score': match_count / len(keywords) if keywords else 0
            })
    
    # Sort by match score
    results.sort(key=lambda x: x['_match_score'], reverse=True)
    
    if results and len(results) <= 3:
        for r in results:
            print(f"[DEBUG] Match ({r['_match_score']:.1%}): {r['base_name']}")
    
    return results


def extract_specs_from_query(query: str) -> Dict:
    """Extract specifications mentioned in user query."""
    specs = {}
    
    # ขนาด
    size_match = re.search(r'(\d+)\s*นิ้ว', query)
    if size_match:
        specs['ขนาด'] = f"{size_match.group(1)} นิ้ว"
    
    # โครง
    if 'เหล็ก' in query:
        specs['โครง'] = 'เหล็ก'
    elif 'ไฟเบอร์' in query:
        specs['โครง'] = 'ไฟเบอร์'
    
    # สี
    if 'สีตาย' in query:
        specs['สี'] = 'สีตาย'
    elif 'ไล่ระดับสี' in query or 'ไล่ระดับ' in query:
        specs['สี'] = 'ไล่ระดับสี'
    
    return specs


def extract_quantity(query: str) -> tuple[int, str]:
    """Extract quantity from query and return (quantity, cleaned_query)."""
    # Look for patterns like "2 อัน", "10 ชิ้น", etc.
    patterns = [
        r'(\d+)\s*(?:อัน|ชิ้น|ตัว|ใบ|แผ่น)',
    ]
    
    cleaned_query = query
    quantity = 1
    
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            quantity = int(match.group(1))
            # Remove quantity part from query
            cleaned_query = re.sub(pattern, '', query).strip()
            break
    
    return quantity, cleaned_query


def match_variant(items: List[Dict], specs: Dict) -> Optional[Dict]:
    """Match specific variant based on extracted specs."""
    best_match = None
    best_score = 0
    
    for item in items:
        # Check if all specs match
        match_score = 0
        for key, value in specs.items():
            if key in item['specs'] and item['specs'][key] == value:
                match_score += 1
        
        # Perfect match: all provided specs match
        if match_score == len(specs) and match_score > 0:
            if match_score > best_score:
                best_match = item
                best_score = match_score
    
    return best_match


def get_clarification_questions(base_name: str, provided_specs: Dict) -> List[str]:
    """Generate clarification questions for missing specs."""
    if base_name not in VARIANTS:
        return []
    
    metadata = VARIANTS[base_name]
    questions = []
    
    for dim_name, dim_spec in metadata['dimensions'].items():
        # Check if this dimension is already specified
        if dim_name not in provided_specs:
            questions.append(dim_spec['question'])
    
    return questions


def process_query(query: str, verbose: bool = True) -> Dict:
    """Process a user query and return response."""
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"User: {query}")
        print(f"{'='*80}\n")
    
    # Step 1: Extract quantity and clean query
    quantity, cleaned_query = extract_quantity(query)
    if verbose:
        print(f"📊 Quantity: {quantity}")
        if cleaned_query != query:
            print(f"🧹 Cleaned query: {cleaned_query}")
    
    # Step 2: Search products
    results = search_products(cleaned_query)
    if verbose:
        print(f"🔍 Found {len(results)} matching items")
    
    if not results:
        return {
            'status': 'not_found',
            'message': 'ไม่พบสินค้าที่ตรงกับคำค้นหา'
        }
    
    # Step 3: Extract specs from cleaned query
    specs = extract_specs_from_query(cleaned_query)
    if verbose and specs:
        print(f"📋 Specs from query: {specs}")
    
    # Step 4: Check if multiple variants exist
    base_names = list(set(item['base_name'] for item in results))
    
    if len(base_names) == 1 and len(results) > 1:
        # Multiple variants of same product
        base_name = base_names[0]
        
        # Try to match specific variant
        matched = match_variant(results, specs)
        
        if matched:
            # Found exact match
            total = matched['winner_price'] * quantity
            
            if verbose:
                print(f"\n✅ Matched: {matched['item_id']}")
                print(f"   {matched['full_name']}")
            
            return {
                'status': 'success',
                'item': matched,
                'quantity': quantity,
                'unit_price': matched['winner_price'],
                'total_price': total,
                'message': f"{matched['full_name']}\nราคา {matched['winner_price']:.2f} บาท ({matched['winner_vendor']})\nจำนวน {quantity} = {total:.2f} บาท"
            }
        else:
            # Need clarification
            questions = get_clarification_questions(base_name, specs)
            
            if verbose:
                print(f"\n❓ Need clarification for: {base_name}")
                print(f"   Variants: {len(results)}")
            
            return {
                'status': 'need_clarification',
                'base_name': base_name,
                'variants': results,
                'questions': questions,
                'message': f"พบ {base_name} {len(results)} แบบ:\n" + '\n'.join(questions)
            }
    
    elif len(results) == 1:
        # Single item, no ambiguity
        item = results[0]
        total = item['winner_price'] * quantity
        
        if verbose:
            print(f"\n✅ Found: {item['item_id']}")
        
        return {
            'status': 'success',
            'item': item,
            'quantity': quantity,
            'unit_price': item['winner_price'],
            'total_price': total,
            'message': f"{item['full_name']}\nราคา {item['winner_price']:.2f} บาท ({item['winner_vendor']})\nจำนวน {quantity} = {total:.2f} บาท"
        }
    
    else:
        # Multiple different products
        return {
            'status': 'multiple_products',
            'items': results,
            'message': f'พบหลายสินค้า:\n' + '\n'.join(f"• {item['base_name']}" for item in results[:5])
        }


def main():
    """Run test scenarios."""
    
    print("=== LLM CHATBOT TEST SCENARIOS ===\n")
    
    test_cases = [
        # Scenario 1: Complete query (no clarification needed)
        "ร่มโค้ก 36 นิ้ว โครงไฟเบอร์ สีตาย 2 อัน",
        
        # Scenario 2: Incomplete query (need clarification)
        "ร่มโค้ก 10 อัน",
        
        # Scenario 3: Partial specs
        "ร่มโค้ก 36 นิ้ว เหล็ก 5 อัน",
        
        # Scenario 4: Single item (no variants)
        "กล่องทิชชู 3 อัน",
    ]
    
    for query in test_cases:
        result = process_query(query)
        
        print("\n" + "─"*80)
        print("Agent Response:")
        print("─"*80)
        print(result['message'])
        
        if result['status'] == 'need_clarification':
            print("\n[Waiting for user to specify...]")


if __name__ == '__main__':
    main()
