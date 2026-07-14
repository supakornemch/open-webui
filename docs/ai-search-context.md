# AI Search Context — สำหรับ Planner / Decision Making

> **Updated:** 2026-07-03 | **Source:** AI Search ingestion setup session

---

## ⚠️ AI Search Tier Requirement (Critical Decision)

**ต้องใช้ Basic tier ขึ้นไปเสมอ** สำหรับระบบ RAG/Agentic Retrieval — Free tier ไม่เพียงพอ

| Feature | Free | Basic | S1 |
|---|---|---|---|
| Vector Search | ❌ | ✅ | ✅ |
| Semantic Ranker | ❌ (free เท่านั้น) | ✅ Standard | ✅ Standard |
| Skillsets (auto-chunk/embed) | ❌ | ✅ | ✅ |
| Agentic Retrieval (Knowledge Base) | ❌ | ✅ | ✅ |
| Index Projections | ❌ | ✅ | ✅ |
| Storage | 50 MB | 2 GB | 25 GB/partition |
| Indexes | 3 | 15 | 50 |
| MCP Endpoint | ❌ | ✅ | ✅ |

---

## 💰 Pricing (Southeast Asia, USD)

| Tier | Cost/SU | Min Config | Monthly |
|---|---|---|---|
| **Free** | $0 | — | $0 |
| **Basic** | ~$73 | 1 SU | **~$73** |
| **Standard S1** | ~$250 | 1 SU | **~$250** |
| **Standard S2** | ~$1,000 | 1 SU | **~$1,000** |

### Additional Costs

| Component | Cost |
|---|---|
| Semantic Ranker | First 1,000 req/mo free; then ~$0.50/1,000 |
| Agentic Retrieval (query planning) | Azure OpenAI token costs (~$4/2,000 queries with gpt-4o-mini) |
| Skillset execution | Per-1,000 executions pricing |
| text-embedding-3-large | ~$0.13/1M tokens |

---

## 📊 Budget Impact (with Container Apps stack)

| Scenario | Without AI Search | With AI Search Basic |
|---|---|---|
| **Typical POC** (8h/day) | ~$35/mo | **~$108/mo** ⚠️ |
| **Minimal** (scale-to-zero) | ~$20/mo | **~$90/mo** |

> ⚠️ AI Search Basic ($73/mo 24/7 — ไม่มี scale-to-zero) ทำให้เกินงบ $100 เล็กน้อย

---

## 🔄 Alternatives (for budget-constrained POC)

| Approach | Cost | Feature Parity |
|---|---|---|
| **pgvector on PostgreSQL** (ใช้ DB เดิม) | $0 | Basic RAG, no semantic ranker, no agentic |
| **Azure AI Search Free** | $0 | BM25 only, 50MB, 3 indexes, no vector |
| **AI Search Basic** | ~$73/mo | Full RAG + Agentic |

---

## ✅ Recommended Path

1. **POC Phase 1**: pgvector (ฟรี) → validate RAG use case
2. **POC Phase 2**: Upgrade to AI Search Basic (~$73/mo) → agentic retrieval
3. **Production**: AI Search Standard S1 (~$250/mo) → scale + SLA

---

## 🏗️ Current State (as of 2026-07-03)

| Resource | Name | Tier | Status |
|---|---|---|---|
| AI Search | `srch-entchat-poc-sea-basic` | Basic | ✅ Running |
| Index | `haadthip-docs` | — | 14/19 PDFs indexed |
| Knowledge Base | `haadthip-kb` | — | Not yet created |
| Embedding Model | `text-embedding-3-large` | Standard | ✅ Deployed |

---

## 🔗 Related Docs

- `docs/ai-search-ingestion-guide.md` — Full ingestion + agentic retrieval guide
- `docs/aca-deployment-spec.md` — Container Apps deployment spec (updated with AI Search)
- `docs/aks-deployment-spec.md` — AKS deployment spec (updated with AI Search)
- `scripts/ingest-blob-to-search-v2.py` — Python ingestion script
- `scripts/setup-auto-ingest.sh` — REST API pipeline setup
