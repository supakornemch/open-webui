# E-Expense FAQ Search — Architecture & Schema Design

## ภาพรวม (Overview)

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Excel Q&A   │────▶│  Flatten Script  │────▶│  eexpense-faq.jsonl │
│  (Decision   │     │  (Trace paths)   │     │  (41 docs)          │
│   Tree)      │     └──────────────────┘     └────────┬────────────┘
└──────────────┘                                       │
                                                       ▼
                                             ┌──────────────────┐
                                             │  Embed + Upload  │
                                             │  (text-embedding │
                                             │   3-large, 3072d)│
                                             └────────┬─────────┘
                                                      │
                                                      ▼
┌──────────────────┐                      ┌─────────────────────┐
│  Chatbot Engine  │◀─────────────────────│  Azure AI Search    │
│  (FAQ + State    │    Hybrid Search     │  eexpense-faq-idx   │
│   Machine)       │    BM25+Vector+Sem   │                     │
└──────────────────┘                      └─────────────────────┘
```

---

## 📁 ไฟล์ (Files)

| File | Purpose |
|---|---|
| `scripts/flatten-eexpense-qa.py` | Parse Excel → Trace decision tree → Output JSONL |
| `scripts/create-eexpense-index.py` | Create Azure AI Search index with schema |
| `scripts/ingest-eexpense-faq.py` | Embed documents + upload to search index |
| `scripts/eexpense-chatbot.py` | Chatbot engine: search + state machine |
| `scripts/setup-eexpense-search.sh` | All-in-one pipeline script |
| `data/eexpense-faq.jsonl` | Flattened FAQ documents (41 docs) |

---

## 🗄️ Azure AI Search Schema (`eexpense-faq-idx`)

| Field | Type | Purpose | Searchable | Filterable | Facetable |
|---|---|---|---|---|---|
| `id` | `Edm.String` | Unique doc ID (Key) | ❌ | ✅ | ❌ |
| `question` | `Edm.String` | Enriched question (root + conditions) | ✅ (thai.microsoft) | ❌ | ❌ |
| `answer` | `Edm.String` | Full answer text | ✅ (thai.microsoft) | ❌ | ❌ |
| `shortAnswer` | `Edm.String` | Summarized answer (1 sentence) | ✅ (thai.microsoft) | ❌ | ❌ |
| `category` | `Edm.String` | Topic category | ❌ | ✅ | ✅ |
| `keywords` | `Collection(Edm.String)` | Search keywords | ✅ (thai.microsoft) | ❌ | ❌ |
| `conditions` | `Collection(Edm.String)` | Branching conditions | ✅ | ✅ | ❌ |
| `contextQuestions` | `Collection(Edm.String)` | Breadcrumb trail | ✅ | ❌ | ❌ |
| `sourceId` | `Edm.String` | Original ANS id | ❌ | ✅ | ❌ |
| `choiceType` | `Edm.String` | button / info | ❌ | ✅ | ✅ |
| `contentVector` | `Collection(Edm.Single)` | Embedding (3072d) | ✅ (vector) | ❌ | ❌ |

### Vector Search Configuration
- **Algorithm**: HNSW, cosine similarity, m=4, efConstruction=400, efSearch=500
- **Dimensions**: 3072 (text-embedding-3-large)
- **Profile**: `eexpense-vector-profile`

### Semantic Configuration
- **Title field**: `question`
- **Content fields**: `answer`, `keywords`
- **Keywords fields**: `keywords`, `category`

---

## 🧠 การ Flatten Decision Tree → FAQ Documents

### หลักการ (Principle)

จาก Excel ที่เป็น Decision Tree:

```
Q1: ขอล่วงหน้ากี่วัน? → Q2: มีทดรองจ่ายไหม?
  ├─ A: มี → ANS1
  └─ B: ไม่มี → ANS2
```

Flatten เป็น 2 documents:

```json
{
  "id": "Q1_ANS1_มีขอทดรองจ่ายหรือไม่____A",
  "question": "ต้องคีย์ขอแผนการเดินทางล่วงหน้าอย่างน้อยกี่วัน เมื่อมีขอทดรองจ่าย? → มี?",
  "answer": "การขอทดรองจ่ายจะต้องขอล่วงหน้า... อย่างน้อย 3 วัน...",
  "conditions": ["มีขอทดรองจ่ายหรือไม่? → A : มี"],
  "contextQuestions": ["Q1: ...", "Q2: มีขอทดรองจ่ายหรือไม่? → A : มี"]
}
```

### Key Design Choices

1. **Root question เป็น main topic** — ใช้คำถามแรกในเส้นทางเป็น `question` หลัก
2. **Conditions แยกเป็น array** — ทำให้ filter ได้ และใช้สร้าง clarification question
3. **Unique ID รวม root + conditions** — ป้องกัน collision ระหว่างเส้นทางที่ใช้ branching node เดียวกัน (เช่น Q2, Q4, Q16 ถามเหมือนกันแต่ root ต่างกัน)
4. **Only true roots** — เฉพาะ Q nodes ที่ไม่มีใครชี้มาเท่านั้นที่เป็น entry point (27 roots จาก 33 nodes)

### Categories (11 หมวดหมู่)

| Category | Count | Example |
|---|---|---|
| ค่าอาหาร/เบี้ยเลี้ยง | 12 | Level 1-8, หักอาหารเช้า, วันหยุด |
| ผู้ร่วมเดินทาง | 5 | Cost Center เดียว/ต่าง, รวม/แยก |
| การแก้ไข/ยกเลิกเอกสาร | 5 | Withdraw, Terminate, Cancel Trip |
| แผนการเดินทาง | 4 | One-day trip, ย้อนหลัง, แก้ไขวันที่ |
| การขอทดรองจ่าย | 3 | ขอล่วงหน้า, 3 วัน |
| สิทธิ์การเบิก | 3 | Outsource, ทำแทน, Requestor |
| การอนุมัติ | 2 | Approver, Delegate |
| Cost Center | 2 | แก้ไข, ดึงจาก AD |
| ข้อมูลระบบ | 2 | E-Expense คืออะไร, รองรับอะไรบ้าง |
| ไฟล์แนบ | 2 | ประเภท, ขนาด |
| ประวัติเอกสาร | 1 | User Inbox/History |

---

## 🔄 Search Strategy (Hybrid)

```
User Query
    │
    ├──▶ Quick Keyword Lookup (fast path, no API call)
    │
    ├──▶ BM25 Full-Text Search (thai.microsoft analyzer)
    │        +
    ├──▶ Vector Search (text-embedding-3-large, cosine)
    │        │
    │        ▼
    │    RRF Fusion (Reciprocal Rank Fusion)
    │        │
    │        ▼
    │    Semantic Ranker (re-rank top results)
    │
    ▼
  Top-N Results
    │
    ▼
  State Machine
    ├── 1 result, no conditions → Direct Answer
    ├── Multiple variants, same sourceId → Ask Clarification
    ├── Multiple sourceIds → Return Best Match + Suggestions
    └── No results → Fallback Response
```

---

## 🚀 วิธีใช้งาน (Usage)

### 1. Full Pipeline (One-shot)
```bash
export AZURE_SEARCH_KEY="..."
export AZURE_OPENAI_API_KEY="..."
./scripts/setup-eexpense-search.sh
```

### 2. Step-by-step
```bash
# Step 1: Flatten Excel
python3 scripts/flatten-eexpense-qa.py \
    --excel "path/to/Q&A สำหรับ chatbot_E-Expense.xlsx" \
    --pretty  # optional: output formatted JSON

# Step 2: Create Index
python3 scripts/create-eexpense-index.py --force

# Step 3: Embed + Upload
python3 scripts/ingest-eexpense-faq.py --reset

# Step 4: Test Chatbot
python3 scripts/eexpense-chatbot.py
```

### 3. As Library (in your chatbot code)
```python
from scripts.eexpense_chatbot import EExpenseChatbot

bot = EExpenseChatbot()
result = bot.ask("ขอล่วงหน้ากี่วัน")

if result["type"] == "answer":
    print(result["text"])          # Full answer
    print(result["sourceId"])      # ANS1
elif result["type"] == "clarify":
    for choice in result["choices"]:
        print(choice["label"])     # Show options to user
```

---

## 🔮 Future Enhancements

1. **Azure AI Foundry Knowledge Base** — Wrap the index as a Knowledge Source for agentic retrieval
2. **Open WebUI Pipe** — Integrate as a Pipe function alongside existing Haadthip Knowledge Pipe
3. **Auto-refresh** — Watch Excel file for changes → auto re-index
4. **Analytics** — Track top questions, success rate, clarification rate
5. **Multi-language** — Add English translations for international employees
