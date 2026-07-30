# Entity Matching Fix — Architecture Diagrams

## 1. Overall Data Flow

```mermaid
flowchart LR
    subgraph Input["📂 Data Sources"]
        EXCEL["Trade Marketing Materials<br/>price for Y2026.final.xlsx<br/>(7 sheets)"]
    end

    subgraph Parser["🐛 Parser (excel_to_json.py)"]
        direction TB
        PARSE["parse_printing_rate()"]
        BUG1["❌ Bug#1: col_offset=0<br/>item_name='1','2','3'...<br/>Arch data lost!"]
        FIX1["✅ Fix: auto-detect<br/>where 'ลำดับ' column is<br/>→ col_offset=0 or 1"]
        PARSE --> BUG1
        BUG1 -->|Fixed| FIX1
    end

    subgraph JSON["📄 JSON (5 sheets, 251 items)"]
        POSM["1.POSM(MKT) — 25 items"]
        PRINT["2.Printing(MKT) — 13 items"]
        GARM["3.Garment — 16 items"]
        PREM["4.สรุปPremium — 15 items"]
        RATE["5.Printing-Rate — 182 items<br/>(was 162, +20 from fix)"]
    end

    subgraph Converter["🔧 Data Converter (update_tool_data.py)"]
        COMPACT["convert to compact format<br/>{n, t, p, v}"]
        RANGE_FIX["Fix: parse qty ranges<br/>'1-10' → start=1<br/>'1,001-1,500' → start=1001"]
    end

    subgraph Tool["🛠️ OWUI Tool (procurement_price_lookup)"]
        direction TB
        TOKEN["🐛 Bug#2: Old _tokenize()<br/>split words only<br/>'80x100' = single token"]
        DIM_TOKEN["✅ New _tokenize()<br/>'80x100' → ['80x100','80','100','80x100']<br/>+ sorted version for swapped dims"]
        SCORE["New _match_score()<br/>70% text + 30% dimension"]
        SEARCH["search_items() + lookup_price()"]
        TOKEN -->|Fixed| DIM_TOKEN
        DIM_TOKEN --> SCORE
        SCORE --> SEARCH
    end

    subgraph Model["🤖 OWUI Model (procurement-ai-v1)"]
        SP["System Prompt"]
        SKILL["Agent Skill Instruction<br/>(procurement-agent)"]
    end

    EXCEL --> PARSE
    FIX1 --> JSON
    JSON --> Converter
    COMPACT --> Tool
    RANGE_FIX --> Tool
    SEARCH --> Model
    SP --> Model
    SKILL --> Model

    style BUG1 fill:#ff6b6b,color:#fff
    style BUG2 fill:#ff6b6b,color:#fff
    style FIX1 fill:#51cf66,color:#fff
    style DIM_TOKEN fill:#51cf66,color:#fff
    style SCORE fill:#51cf66,color:#fff
```

---

## 2. Bug #1: Parser Column Offset

```mermaid
flowchart TB
    subgraph "Sheet: 5.Printing-Rate1-43"
        direction LR
        R0["Row 2 (header)<br/>[nan] [ลำดับ] [รายการ] [QTY] [vendor...]"]
        R1["Row 3 (data)<br/>[nan] [1] [Arch 60x70 cm...] [1-10] [155...]"]
        R2["Row 4 (data)<br/>[nan] [nan] [nan] [11-20] [150...]"]
    end

    subgraph "❌ Old Parser (hardcode col 0,1,2)"
        OLD1["row[0]='nan' → item_no=''"]
        OLD2["row[1]='1' → item_name='1' ❌"]
        OLD3["row[2]='Arch 60x70...' → qty='Arch...' ❌"]
        OLD4["row[3]='1-10' → vendor_start=3 ❌"]
    end

    subgraph "✅ New Parser (auto-detect col_offset)"
        NEW1["Find column with 'ลำดับ' → col 1"]
        NEW2["col_offset=1"]
        NEW3["row[1]='1' → item_no='1' ✅"]
        NEW4["row[2]='Arch 60x70 cm...' → item_name ✅"]
        NEW5["row[3]='1-10' → qty='1-10' ✅"]
        NEW6["row[4] → vendor_start=4 ✅"]
    end

    R0 --> OLD1
    R1 --> OLD2
    R1 --> NEW3
    R1 --> NEW4
    R1 --> NEW5

    style OLD2 fill:#ff6b6b,color:#fff
    style OLD3 fill:#ff6b6b,color:#fff
    style OLD4 fill:#ff6b6b,color:#fff
    style NEW3 fill:#51cf66,color:#fff
    style NEW4 fill:#51cf66,color:#fff
    style NEW5 fill:#51cf66,color:#fff
```

---

## 3. Bug #2: Dimension-Aware Tokenizer

```mermaid
flowchart TB
    subgraph Query["🔍 User Query"]
        Q["'Wrap around 80x100 cm'"]
    end

    subgraph Old["❌ Old Tokenizer"]
        direction TB
        OT["re.split(r'[\s,/.()-]+')"]
        OT1["['wrap', 'around', '80x100', 'cm']"]
        OT2["Match '80x100' vs '120x50'? NO MATCH"]
        OT3["But 'wrap'+'around' = 2 matches → 67%"]
        OT4["→ False positive: 'Wrap Around Top Shelf 120x50' ❌"]
    end

    subgraph New["✅ New Tokenizer"]
        direction TB
        NT["Step 1: Same split"]
        NT1["['wrap', 'around', '80x100', 'cm']"]
        NT2["Step 2: Detect NxM pattern"]
        NT3["'80x100' → expand:"]
        NT4["['80x100', '80', '100', '80x100']"]
        NT5["Step 3: Sorted version for swapped dims"]
        NT6["(same for '80x100', but '90x60' adds '60x90')"]
    end

    subgraph Score["📊 Split Scoring"]
        direction LR
        TS["Text Score (70%)<br/>['wrap','around']"]
        DS["Dimension Score (30%)<br/>['80x100','80','100','80x100']"]
        TS -->|match words| TSR["vs DB text tokens"]
        DS -->|match numbers| DSR["vs DB dim tokens"]
        TSR --> COMBINED["Combined Score<br/>= 0.7 × text + 0.3 × dim"]
        DSR --> COMBINED
    end

    Q --> Old
    Q --> New
    New --> Score
    Score --> COMBINED

    style OT4 fill:#ff6b6b,color:#fff
    style NT3 fill:#51cf66,color:#fff
    style NT5 fill:#51cf66,color:#fff
    style COMBINED fill:#51cf66,color:#fff
```

---

## 4. Swapped Dimension Resolution

```mermaid
flowchart LR
    subgraph "Query: 'Arch 90x60'"
        Q1["Tokens from tokenizer:<br/>['arch','90x60','90','60','60x90']"]
    end

    subgraph "DB: 'Arch 60x90 cm.'"
        Q2["Tokens from tokenizer:<br/>['arch','60x90','60','90','cm']"]
    end

    subgraph "Match"
        M1["Text: 'arch' == 'arch' → 100%"]
        M2["Dim overlap: {'60x90','60','90'} / {'90x60','90','60','60x90'}"]
        M3["= 3/4 = 75%"]
    end

    subgraph "Result"
        R1["Score = 0.7×100% + 0.3×75% = 92.5%"]
        R2["✅ Found: 'Arch 60x90 cm.'"]
    end

    Q1 --> M2
    Q2 --> M2
    Q1 --> M1
    Q2 --> M1
    M1 --> R1
    M2 --> R1
    R1 --> R2

    style R2 fill:#51cf66,color:#fff
```

---

## 5. Search Lifecycle (end-to-end)

```mermaid
sequenceDiagram
    actor User
    participant Model as 🤖 procurement-ai-v1
    participant Tool as 🛠️ procurement_price_lookup
    participant Data as 📦 Compact JSON (251 items)

    User->>Model: "ขอราคา Arch 90x60 cm จำนวน 10 ชิ้น"
    Model->>Model: System prompt: "ใช้ keyword สั้นๆ"
    Model->>Tool: search_items(query="Arch 90x60")

    Tool->>Tool: _tokenize("Arch 90x60")
    Note over Tool: ['arch','90x60','90','60','60x90']

    Tool->>Data: Scan all 251 items
    Note over Data: _match_score("Arch 90x60", "Arch 60x90...")
    Note over Data: text: 'arch'=='arch' ✅
    Note over Data: dim: '60x90' overlap '60x90' ✅
    Note over Data: score = 92%

    Data-->>Tool: [{item: "Arch 60x90 cm...", score: 0.92, price: 185}]
    Tool-->>Model: {found: true, results: [...]}

    Model->>Tool: lookup_price(item_name="Arch 60x90", quantity=10)

    Tool->>Data: Find best tier for qty=10
    Note over Data: tiers: q=1 (1-10), q=11 (11-20)
    Note over Data: 10 >= 1 → tier q=1, price=185

    Data-->>Tool: {unit: 185, total: 1850}
    Tool-->>Model: {found: true, unit: 185, total: 1850}

    Model->>User: "🔍 Arch 60x90 cm. (match 92%)"
    Model->>User: "💰 185 บาท/ชิ้น × 10 = 1,850 บาท"
    Model->>User: "⚠️ ราคาไม่รวม VAT 7%"
```

---

## 6. Key Files Changed

```mermaid
flowchart TD
    subgraph F1["excel_to_json.py"]
        A1["parse_printing_rate()<br/>+ col_offset detection"]
        A2["convert_printing_mkt()<br/>+ qty range parsing"]
    end

    subgraph F2["update_tool_data.py"]
        B1["TOOL_CODE string"]
        B2["_tokenize(): dimension expand"]
        B3["_is_dim_token(): NxM detection"]
        B4["_match_score(): 70/30 split"]
    end

    subgraph F3["agent_skill_instruction.md"]
        C1["Agent Skill content"]
        C2["5 category guide"]
        C3["Search strategy rules"]
    end

    subgraph F4["OWUI Resources"]
        D1["Tool: procurement_price_lookup (updated)"]
        D2["Skill: procurement-agent (created)"]
        D3["Model: procurement-ai-v1<br/>skillIds + system prompt"]
    end

    A1 --> F1
    B2 --> F2
    B3 --> F2
    B4 --> F2
    C1 --> F3

    F1 -->|generates| D1
    F2 -->|pushes| D1
    F3 -->|creates| D2
    D2 --> D3
    D1 --> D3
```

---

## Summary: Before vs After

| Dimension | Before | After |
|---|---|---|
| **Parser** | col 0,1,2 hardcoded | auto-detect `col_offset` |
| **Item names** | `"1", "2", "3"` (Arch items) | `"Arch 60x70 cm..."` |
| **Token count** | 231 | **251** (+20 revealed) |
| **Tokenizer** | word split only | + dimension expansion (`NxM`→`N,M,sorted`) |
| **Scoring** | single text score | **70% text + 30% dimension** |
| **Swapped dims** | `60x90` ≠ `90x60` | `60x90` matches `90x60` ✅ |
| **Wrap around 80x100** | ❌ false match to 120x50 | ✅ correct match 100% |
| **Arch 90x60** | ❌ not found | ✅ 92% match to Arch 60x90 |
