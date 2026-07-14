# Session 6 — 2026-07-03: Foundry Integration + Index Fix

## What We Did

### 1. Foundry Hub → AI Services Connection
- Created `azure_ai_services` connection in Hub `aif-entchat-poc-sea`
- Type: `azure_ai_services`, auth: `aad` (Managed Identity)
- `is_shared: true` → Project `proj-entchat-poc-sea` auto-sees it
- YAML: `EnterpriseChat/config/hub-ai-services-connection.yaml`

### 2. KB Endpoint Fix
- **Problem**: KB used `services.ai.azure.com` → "Could not reach the model endpoint"
- **Root cause**: `services.ai.azure.com` = Foundry management API, NOT model inference
- **Fix**: Switched to `cognitiveservices.azure.com` (the actual inference endpoint)
- KB now: `resourceUri: https://aisrv-entchat-poc-sea.cognitiveservices.azure.com` + MI (no apiKey)

### 3. Index Recreation (v2)
- **Problem**: 2 docs failed — `content` field had `facetable: true` → entire content = single term > 32766 bytes
- **Fix**: Created `haadthip-public-idx-v2` with `facetable: false` on content field
- Also added semantic config: `haadthip-semantic` with prioritized fields

### 4. Indexer v2
- Created `haadthip-public-idxr-v2` pointing to new index
- **Result: 18/18 documents indexed, 0 failures** 🎉

### 5. Knowledge Source Update
- Updated `haadthip-ks` → `searchIndexName: haadthip-public-idx-v2`

### 6. Agentic Retrieval Test
```json
POST /knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01
{
  "intents": [{"search": "What is Haadthip company and what products do they sell?", "type": "semantic"}],
  "knowledgeSourceParams": [{"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}],
  "maxOutputSizeInTokens": 5000
}
```
**Result**: 4 search hits, 29,645 reasoning tokens — pipeline fully working!

### 7. KB Managed Identity
- Verified: `apiKey: null, authIdentity: null` → SystemAssigned MI auto-detected
- Pattern: omit BOTH fields, don't set `authIdentity: { identityType: "SystemAssigned" }` (that's an abstract class error)

## Architecture

```
Foundry Hub (aif) → connection → AIServices (aisrv) ← model inference ← AI Search KB (haadthip-kb)
                       ↑ mgmt                   ↑ inference
Foundry Project (proj)                         cognitiveservices.azure.com
```

## Key Learnings

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `services.ai.azure.com` unreachable | Management API, not inference | Use `cognitiveservices.azure.com` |
| Content field term-too-large | `facetable: true` on large field | Set `facetable: false`, recreate index |
| Cannot modify existing field | AI Search limitation | Create new index (v2) |
| `maxOutputSizeInTokens` < 5000 | API requirement | Set ≥ 5000 |
| MI `authIdentity` abstract class | Wrong JSON format | Omit both `apiKey` and `authIdentity` |

## Remaining Limitations
- **Basic tier**: Content truncated at 524,288 chars (`htc-one-report-2024-en.pdf` partially truncated)
- **Basic tier**: File max 16 MB (`htc-sustainability-report-2024-en.pdf` — metadata only)
- **Cross-language**: Thai queries don't match English documents (semantic search ≠ translation)

---

## Quick Reference — cURL Examples

### Knowledge Base — Simple Retrieve (English)
```bash
curl -s -X POST "https://srch-entchat-poc-sea-01.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: YOUR_ADMIN_KEY" \
  -d '{
    "intents": [{"search": "What is Haadthip company?", "type": "semantic"}],
    "knowledgeSourceParams": [{"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}],
    "maxOutputSizeInTokens": 5000
  }'
```

### Knowledge Base — Thai Query
```bash
curl -s -X POST "https://srch-entchat-poc-sea-01.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: YOUR_ADMIN_KEY" \
  -d '{
    "intents": [{"search": "\u0e2b\u0e32\u0e14\u0e17\u0e34\u0e1e\u0e22\u0e4c\u0e04\u0e37\u0e2d\u0e1a\u0e23\u0e34\u0e29\u0e31\u0e17\u0e2d\u0e30\u0e44\u0e23", "type": "semantic"}],
    "knowledgeSourceParams": [{"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}],
    "maxOutputSizeInTokens": 5000
  }'
```

### Knowledge Base — With `az` key inline
```bash
curl -s -X POST "https://srch-entchat-poc-sea-01.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: $(az search admin-key show --service-name srch-entchat-poc-sea-01 --resource-group rg-entchat-poc-sea --query primaryKey -o tsv)" \
  -d '{
    "intents": [{"search": "What is Haadthip company?", "type": "semantic"}],
    "knowledgeSourceParams": [{"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}],
    "maxOutputSizeInTokens": 5000
  }'
```

### Direct Search — Check Index Content
```bash
# Count docs
curl -s "https://srch-entchat-poc-sea-01.search.windows.net/indexes/haadthip-public-idx-v2/docs/\$count?api-version=2024-07-01" \
  -H "api-key: $(az search admin-key show --service-name srch-entchat-poc-sea-01 --resource-group rg-entchat-poc-sea --query primaryKey -o tsv)"

# List all document names
curl -s "https://srch-entchat-poc-sea-01.search.windows.net/indexes/haadthip-public-idx-v2/docs?api-version=2024-07-01&search=*&\$top=20&\$select=metadata_storage_name" \
  -H "api-key: $(az search admin-key show --service-name srch-entchat-poc-sea-01 --resource-group rg-entchat-poc-sea --query primaryKey -o tsv)" \
  | python3 -c "import json,sys; [print(d['metadata_storage_name']) for d in json.load(sys.stdin).get('value',[])]"
```

### Knowledge Source — Check Config
```bash
curl -s "https://srch-entchat-poc-sea-01.search.windows.net/knowledgesources('haadthip-ks')?api-version=2026-04-01" \
  -H "api-key: YOUR_ADMIN_KEY" | python3 -m json.tool
```

### Knowledge Base — Check Config
```bash
curl -s "https://srch-entchat-poc-sea-01.search.windows.net/knowledgebases('haadthip-kb')?api-version=2026-04-01" \
  -H "api-key: YOUR_ADMIN_KEY" | python3 -m json.tool
```

