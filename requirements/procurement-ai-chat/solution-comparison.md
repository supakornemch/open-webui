# Solution Comparison — Procurement AI Chat

> Updated: 21 July 2026

---

## สรุปทางเลือก

หลังจากวิเคราะห์แล้ว มี 3 ทางหลักในการ build ระบบ Procurement AI Chat:

| | **A: OWUI RAG Only** | **B: OWUI Excel Tool** ⭐ | **C: OWUI Azure AI Search** |
|:--|:---:|:---:|:---:|
| Tech | Knowledge (ChromaDB/PGVector) | Tool (pandas + Excel) | Tool + AI Search Index |
| Complexity | ต่ำที่สุด | ต่ำ-ปานกลาง | ปานกลาง |
| Maintenance | Upload ไฟล์ → เสร็จ | แค่ Excel file ใน container | ต้อง manage Azure Search index |
| Accuracy | ⭐⭐ (LLM อนุมานเอง) | ⭐⭐⭐⭐⭐ (deterministic) | ⭐⭐⭐⭐⭐ (deterministic) |
| Latency | ~1-3s (RAG retrieval) | <100ms (in-memory) | ~200-500ms (API call) |
| Cost | ฟรี | ฟรี | Azure AI Search ~$245/mo |
| QTY tier | ❌ LLM guess | ✅ exact logic | ✅ exact logic |
| Fuzzy match | ✅ semantic search | ❌ keyword only | ✅ ✅ semantic + exact |
| Scalability | ✅ auto by OWUI | ⚠️ in-memory (5MB) | ✅ auto by Azure |
| Setup time | 1 hr | 2-4 hrs | 1-2 days |

---

## ⭐ RECOMMENDED: Solution B — Excel Direct Tool

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  OWUI (genie.haadthip.com)                                   │
│                                                              │
│  Model Preset: "Procurement AI"                              │
│  ├── System Prompt (instructions)                           │
│  ├── Tools:                                                 │
│  │   ├── lookup_price() → pandas query Excel               │
│  │   └── calculator() → built-in                           │
│  └── No Knowledge Base needed                              │
│                                                              │
│  LiteLLM → Azure OpenAI (deploy-gpt-5.4-mini)               │
└─────────────────────────────────────────────────────────────┘
```

### How it works
1. User สอบถามราคาใน Chat
2. LLM วิเคราะห์: item name, QTY, color
3. LLM เรียก `lookup_price(item, qty, color)` → function calling
4. Tool อ่าน Excel ด้วย pandas → match item → find QTY tier → apply color adj
5. Tool return JSON → LLM ประกอบภาษา → ตอบ

### ✅ Pros
| | |
|:---|:---|
| 🔧 **Simple** | แค่ 1 Tool + 1 Excel file = ใช้ OWUI features ที่มีอยู่แล้ว |
| 💰 **Zero cost** | ไม่ต้องใช้ Azure AI Search → save ~$245/mo |
| ⚡ **Fast** | pandas in-memory → <100ms per query |
| 🎯 **Accurate** | Deterministic → same input = same output |
| 📦 **Portable** | Excel file + Tool code → export/import ได้ |
| 🔄 **Updatable** | แทนที่ Excel file ใหม่ → ราคาอัพเดททันที |
| 🛡️ **No leaking** | ราคาอยู่ใน container เท่านั้น ไม่ใช่ public index |

### ❌ Cons
| | |
|:---|:---|
| 🔤 **Keyword match** | ต้องพิมพ์ชื่อถูก (เช่น "สติ๊กเกอร์" ≠ "สติกเกอร์") → แก้ด้วย synonym |
| 📊 **Excel structure** | การ parse แต่ละ sheet ต้องแยก logic |
| 📝 **Maintenance** | เปลี่ยน Excel structure → ต้องปรับ code |

### Mitigation
- เพิ่ม **synonym mapping** ใน Tool: `{"สติกเกอร์":"สติ๊กเกอร์", "ไวนิล":"Vinyl"}`
- แยก **parser per sheet** → แต่ละ sheet มี function ของตัวเอง
- **Pre-process** Excel → flat JSON structure → load on init

---

## Option A: OWUI RAG (Knowledge Base)

### ✅ Pros
| | |
|:---|:---|
| 🚀 **Setup เร็ว** | Upload Excel → สร้าง Model → เสร็จ < 1 ชม. |
| 🔍 **Semantic** | LLM ค้นหาด้วยความหมาย → "ป้ายแขวน" ≈ "ป้ายตั้งโต๊ะ" |
| 👶 **Zero code** | ไม่ต้องเขียน Python |

### ❌ Cons
| | |
|:---|:---|
| ❌ **คำนวณผิด** | QTY tier ไม่แม่น — LLM ต้องเดา |
| 🎲 **Inconsistent** | คำถามเดิม ตอบต่างกัน |
| 🐌 **Slow** | RAG retrieval + LLM processing |
| ❌ **No area calc** | ไม่มีการคำนวณ area ที่แน่นอน |

---

## Option C: Azure AI Search (+ Tool)

### ✅ Pros
| | |
|:---|:---|
| 🔍 **Semantic + Exact** | ได้ทั้ง fuzzy match + deterministic calc |
| 📈 **Scalable** | Support หลาย index, หลาย skill |
| 🔗 **Reuse** | ใช้ infrastructure ที่มีอยู่ (srch-entchat-poc-sand) |

### ❌ Cons
| | |
|:---|:---|
| 💰 **Cost** | AI Search Standard = ~$245/mo |
| 🔧 **Complex** | ต้องสร้าง index + upload data + manage |
| ⏰ **Setup** | 1-2 วัน |

---

## 📊 Decision Matrix

| Criteria | Weight | A: RAG | B: Excel Tool ⭐ | C: AI Search |
|:---------|:-----:|:-----:|:-----:|:-----:|
| ความแม่นยำ | 🔴 High | 4/10 | 10/10 | 10/10 |
| ตั้งค่าง่าย | 🟡 Med | 10/10 | 7/10 | 4/10 |
| ดูแลง่าย | 🟡 Med | 10/10 | 8/10 | 4/10 |
| ความเร็ว | 🟢 Low | 5/10 | 10/10 | 7/10 |
| ค่าใช้จ่าย | 🔴 High | 10/10 | 10/10 | 3/10 |
| Semantic | 🟡 Med | 10/10 | 3/10 | 10/10 |
| **TOTAL** | | **8.2** | **8.0** | **6.0** |

---

## 🗺️ Recommended Path

```
Phase 1: Solution B (Excel Tool)
  ├─ 2-4 hrs setup
  ├─ Deterministic pricing
  ├─ MVP → ทดสอบกับ Procurement
  └─ ไม่มี recurring cost

Phase 1.5: Add Synonym + Simple Fuzzy
  ├─ เพิ่ม synonym mapping
  ├─ ใช้ difflib.get_close_matches() 
  └─ เพิ่ม keyword coverage

Phase 2 (optional): Hybrid B + C
  ├─ Azure AI Search สำหรับ semantic lookup → return candidates
  ├─ Excel Tool สำหรับ exact price → deterministic answer
  └─ Best of both worlds
```
