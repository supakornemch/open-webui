# NeuronHub Presentation — Page-by-Page Review

> **ไฟล์:** `docs/หาดทิพย์ NeuronHub_Presentation.pdf` (12 หน้า)
> **เอกสารนี้:** ความเห็น + คำถาม + ข้อสังเกต แยกทีละหน้า

---

## 📄 Page 1 — Cover

> "NeuronHub — Generative AI Gateway developed by IMC Outsourcing
> ศูนย์กลางขับเคลื่อน AI Transformation เพื่อยกระดับองค์กรสู่อนาคต"

### 💬 Comment

- **Generic pitch** — ไม่ได้ระบุว่าแตกต่างจาก AI Gateway เจ้าอื่นอย่างไร (LiteLLM, Portkey, Kong AI, MLflow AI Gateway)
- คำว่า "Gateway" เป็นหมวดสินค้าที่มี open-source ให้เลือกมากมาย — **IMC ควรชี้แจงว่า Gateway นี้พัฒนาเองกี่ % vs ต่อยอดจาก open-source ตัวไหน**

### ❓ คำถาม

> "Gateway" ของ NeuronHub พัฒนาเองทั้งหมด หรือ fork/ต่อยอดจาก open-source ตัวไหน? (เช่น LiteLLM, Portkey, Envoy AI Gateway)

---

## 📄 Page 2 — Why NeuronHub? (Feature Overview)

> 6 Features:
> - Multi-Model Access (GPT, Gemini, Claude, DeepSeek, Perplexity, Llama)
> - Local Knowledge RAG
> - Ready Prompt Library
> - AI Agents (Calendar, Email, Drive, Web Search, Image, MCP)
> - Role Based Access Control
> - Custom Model

### 💬 Comment

| Feature | 🟢 จริง | 🟡 มีแต่ไม่ exclusive | 🔴 Overclaimed |
|---|---|---|---|
| Multi-Model Access | ✅ ใช้ได้จริง | LiteLLM, OpenRouter ทำได้ | — |
| Local Knowledge RAG | ✅ ใช้ได้จริง | Azure AI Search ทำได้+ดีกว่า | — |
| Ready Prompt Library | ✅ มี | ไม่มี technical moat — export ได้ | — |
| AI Agents | ✅ n8n-based | n8n Community ทำแบบนี้เองได้ | — |
| RBAC | ✅ Entra ID | Azure native อยู่แล้ว | — |
| Custom Model | ✅ Local LLM | Ollama/vLLM ทำเองได้ | — |

**ข้อสังเกตสำคัญ:**
- "ลดค่าใช้จ่ายสูงสุดถึง 75%" — เทียบกับอะไร? ช่วยยกตัวอย่าง benchmark หน่อย
- Perplexity — ใช้ API จริงหรือ? Perplexity ไม่มี public API สำหรับ commercial use แบบฟรี
- "ลดค่าใช้จ่าย 75%" — ถ้าเทียบกับ Azure OpenAI อย่างเดียว → แต่ NeuronHub มี Local LLM (2×H100) เดือนละ 5-6 แสน → เงินที่ "ประหยัด" หายไปไหน?

### ❓ คำถาม

> 1. "ลดค่าใช้จ่ายสูงสุดถึง 75%" — เทียบกับ baseline อะไร? ขอดู cost model หน่อย
> 2. Perplexity API — เป็น official commercial API หรือ scrape?
> 3. Ready Prompt Library มีกี่ prompts? ใครเป็นคนดูแลอัปเดตเมื่อ model เปลี่ยน?

---

## 📄 Page 3 — Architecture Diagram

> n8n + Local LLM + Vector DB (Qdrant + AI Search) + PostgreSQL + Azure services + Public LLMs

### 💬 Comment

**สิ่งที่ทำได้ดี:**
- ✅ Architecture ครอบคลุม — n8n, AI Search, Qdrant, PostgreSQL, Azure Front Door, Monitor, Sentinel
- ✅ Private networking — VPN Gateway, Data Subnet แยก
- ✅ Microsoft ecosystem — Entra ID, Fabric, Power BI, Teams, SharePoint

**สิ่งที่สังเกตเห็น:**

1. **Qdrant + Azure AI Search = ซ้ำซ้อน**
   - AI Search มี vector search + hybrid search + semantic ranker ในตัว
   - Qdrant เพิ่ม overhead ในการ sync, maintain, cost
   - **ถาม:** use case อะไรที่ต้องใช้ Qdrant ทั้งที่ AI Search ทำได้?

2. **Azure Virtual Machines (ไม่ใช่ Container Apps)**
   - n8n รันบน VM = no scale-to-zero = จ่าย 24/7
   - Local LLM รันบน VM = จ่าย GPU 24/7 แม้ไม่มีคนใช้
   - **ถาม:** ทำไมไม่ใช้ Container Apps/AKS? IMC ออกแบบให้ enterprise ต้องจ่ายตลอด?

3. **n8n อยู่บน VM แยก**
   - ถ้า n8n เป็นแค่ workflow engine → ทำไมต้อง 8 vCPU + 8GB? workflow ซับซ้อนขนาดนั้นจริงหรือ?

4. **Missing:**
   - ❌ ไม่มี Cache layer (Redis) — ทุก request ไป LLM ซ้ำ
   - ❌ ไม่มี API Gateway / Rate Limiter
   - ❌ ไม่มี Observability stack (Grafana/Prometheus)
   - ❌ ไม่มี CI/CD pipeline สำหรับ prompt/config

### ❓ คำถาม

> 1. Qdrant + AI Search — ใช้ทั้งคู่ทำไม? Qdrant เก็บอะไรที่ AI Search เก็บไม่ได้?
> 2. ทำไมใช้ VM แทน Container Apps/AKS? Cost optimization?
> 3. Architecture มี DR (Disaster Recovery) ไหม? ถ้า Region ล่มทำยังไง?

---

## 📄 Page 4–7 — AI Agents: Text-to-SQL Demo (4 หน้า)

> Text-to-SQL บน Northwind Database + Hybrid RAG + CSV Download

### 💬 Comment

**นี่คือ 4 หน้าใน 12 หน้า = 33% ของพรีเซนต์ — อุทิศให้ demo เดียว**

| หน้า | เนื้อหา |
|---|---|
| 4 | อธิบายฟีเจอร์ — Hybrid RAG + Tool calling + CSV download |
| 5–7 | Screenshots การใช้งาน (ไม่มี text ให้ extract — เป็นรูปภาพ) |

**ข้อสังเกต:**

1. **Text-to-SQL บน Northwind = Demo database ที่เล็กมาก**
   - Northwind มี ~8 tables, ~3,000 records
   - **ถาม:** ทดสอบกับฐานข้อมูลจริงของหาดทิพย์แล้วหรือยัง? ขนาดเท่าไหร่? Complexity?

2. **4 หน้าสำหรับ demo เดียว — เสียพื้นที่**
   - ควรใช้พื้นที่แค่ 1 หน้า แล้วเพิ่ม demo อื่นที่สำคัญกว่า

3. **CSV Download = n8n node พื้นฐาน**
   - n8n มี "Convert to CSV" + "Respond to Webhook" nodes → ทำได้ใน 2 นาที

### ❓ คำถาม

> 1. Text-to-SQL ทดสอบกับฐานข้อมูลหาดทิพย์จริงหรือยัง? กี่ schema? กี่ table? Error rate?
> 2. ถามคำถาม join หลาย table → ยังทำงานได้ไหม? ขอดู accuracy benchmark
> 3. Hybrid RAG ในบริบทนี้หมายถึงอะไร? Semantic search + keyword search? หรือ embedding + BM25?

### 🧪 เสนอขอ Demo เพิ่มเติม — ก่อนตัดสินใจซื้อ

> **Northwind (8 tables, ~3K records) ไม่เพียงพอต่อการประเมินสำหรับ enterprise**
> ควรขอให้ IMC แสดง demo เพิ่มเติมก่อนเซ็นสัญญา:

| # | Demo ที่ควรขอ | ทำไมถึงสำคัญ |
|---|---|---|
| **1** | **Large Database — ฐานข้อมูล ERP จริง** (SAP, Oracle, Dynamics 365) ที่มี 50-100+ tables, หลักล้าน records | Northwind คือของเล่น — โลกจริงมี schema ซับซ้อน หลาย schema, stored procedures, views, indexes — ถ้า NeuronHub พังกับฐานข้อมูลใหญ่ = ใช้จริงไม่ได้ |
| **2** | **NoSQL Database — MongoDB, Azure Cosmos DB** | ข้อมูลในองค์กรไม่ได้มีแค่ relational — documents, key-value, graph databases — NeuronHub บอกว่า "Hybrid RAG" แต่น่าจะใช้แค่ PostgreSQL + AI Search → ต้องพิสูจน์ว่าเชื่อม NoSQL ได้จริง |
| **3** | **Complex Join Query** — "ยอดขายรายเดือนแยกตามภาคของสินค้าหมวด A เทียบกับปีที่แล้ว พร้อม % การเติบโต" | Northwind query ง่ายเกิน — query จริงมัก join 4-6 tables + subquery + aggregation — ถ้าทำไม่ได้ = จบ |
| **4** | **Multi-Turn Conversation** — ถามต่อเนื่อง 3-5 คำถาม โดยอ้างอิงบริบทจากคำถามก่อนหน้า | ผู้ใช้จริงไม่ถามคำถามเดียวแล้วจบ — "ขอข้อมูลลูกค้าในกรุงเทพ... แล้วในนี้ใครซื้อมากสุด... แล้วสินค้าที่เขาซื้อมีอะไรบ้าง" |
| **5** | **Thai Language Query** — ถามภาษาไทย + ชื่อเฉพาะภาษาไทย (ชื่อลูกค้า, ชื่อสินค้า, ชื่อจังหวัด) | ข้อมูลหาดทิพย์เป็นภาษาไทย — Text-to-SQL ต้องเข้าใจภาษาไทย + transliteration ได้ |
| **6** | **Error Handling** — จงใจถามคำถามที่ตอบไม่ได้ (ข้อมูลไม่อยู่, column ไม่มี, logic ผิด) → ระบบตอบยังไง? | ผู้ใช้ถามผิดตลอด — ระบบต้องไม่ hallucinate SQL ที่ผิด หรือ crash |

> ⚠️ **ถ้า IMC ไม่สามารถทำ Demo 6 ข้อนี้ได้ — Text-to-SQL Agent ของ NeuronHub ยังไม่พร้อมสำหรับ production**

---

## 📄 Page 8–9 — Guardian: Rule-Based (2 หน้า)

> Middleware Service → regex-based restricted words → redact ก่อนส่งไป LLM → Web UI for rules management

### 💬 Comment

**Page 8:** Architecture diagram — Gateway → redact → LLM → respond

**สิ่งที่ทำได้ดี:**
- ✅ แนวคิดถูกต้อง — content safety ต้องมีก่อนส่งเข้า LLM
- ✅ Web UI จัดการ rules → non-technical user แก้ไขได้เอง

**ข้อสังเกต:**

1. **Regex-based = ง่ายสุด, evasion ง่ายสุด**
   - คำหยาบ → ใส่เว้นวรรค, เปลี่ยนภาษา, ใช้คำแสลง → หลุด
   - **ถาม:** มีจัดการ evasion pattern ไหม? (Leetspeak, whitespace insertion, homoglyph)

2. **Redact vs Block?**
   - Slide บอก "redaction" (ลบคำต้องห้ามแล้วส่งต่อ)
   - **ถาม:** ถ้าประโยคกลายเป็น nonsense หลัง redact → LLM ตอบอะไร?

3. **Web UI for rules management — ใคร manage?**
   - ถ้าทุกแผนกแก้ rule ได้ → risk of breaking
   - **ถาม:** มี approval workflow ก่อน rule ขึ้น production ไหม?

4. **เทียบกับ Azure AI Content Safety**
   - Azure มี managed service → detect hate speech, violence, self-harm, sexual content → ผ่าน SLA
   - Regex-based = manual rule → ไม่มี ML → false negative สูง

### ❓ คำถาม

> 1. จัดการ evasion (ลีทสปีค, ช่องไฟ, เปลี่ยนภาษา) ได้ไหม?
> 2. Rule approval workflow — ใคร approve ก่อน deploy?
> 3. เทียบกับ Azure AI Content Safety — จุดที่ regex-based ดีกว่า?

---

## 📄 Page 10–11 — Guardian: Local LLM Inspection (2 หน้า)

> Regex-based → ถ้าไม่เจอ → LLM-based inspection → force respond with warning / send to target model

### 💬 Comment

**Page 10:** 2-layer architecture
```
Request → Regex (Layer 1) → No match? → Local LLM (Layer 2) → 
  → Found → Warning response
  → Not found → Send to target LLM → Return response
```

**สิ่งที่สังเกต:**

1. **Local LLM inspect ทุก request = Latency ×2 + Cost เพิ่ม**
   - Request → Local LLM (0.5-3 วิ) → Target LLM (1-5 วิ) = รวม 1.5-8 วิ
   - ผู้ใช้รอ 8 วินาที → UX พัง
   - **ถาม:** Latency เพิ่มเท่าไหร่เมื่อเปิด Guardian? มีตัวเลข benchmark ไหม?

2. **Local LLM ตัวไหน?**
   - Slide ไม่ระบุว่าใช้ model อะไร inspect
   - ถ้าใช้ Gemma/H100 → จ่าย 5-6 แสน/เดือน เพื่อ inspect text อย่างเดียว?
   - **ถาม:** ใช้ Gemma บน H100 inspect content หรือใช้ small model (Phi-3, Llama 8B)?

3. **Cost การ inspect:**
   - ทุก request ต้องผ่าน Local LLM ก่อน → GPU ต้องพร้อมตลอด (no scale-to-zero)
   - **ถาม:** ถ้ามี 1,000 requests/วัน → Local LLM ใช้ทรัพยากรเท่าไหร่? คุ้มไหมกับการเปิด H100 ตลอด?

4. **False Positive / False Negative**
   - LLM-based guard → hallucination → block คำถามปกติ หรือปล่อยคำถามอันตราย
   - **ถาม:** มี eval dataset ทดสอบ accuracy Guardian ไหม? Precision/Recall?

5. **เทียบกับ Azure AI Content Safety:**
   - Azure: Managed, SLA, $1/1,000 texts, latency ~50ms
   - NeuronHub: Self-managed, H100 cost, latency ~0.5-3 วิ

### ❓ คำถาม

> 1. Guardian latency เพิ่มเท่าไหร่? ขอ benchmark หน่อย
> 2. Local LLM inspect ใช้ model อะไร? จำเป็นต้องใช้ H100 ไหม?
> 3. ถ้าเปิด Guardian → GPU ต้อง Always-on? ปิด Guardian ได้ไหมถ้าไม่ต้องการ?
> 4. มี eval dataset วัด accuracy Guardian (precision/recall/F1) ไหม?

---

## 📄 Page 12 — Contact Us

> neuronhub@imcinstitute.com / 099-347-9694 / 088-192-7975 / 065-623-2414

### 💬 Comment

- ✅ มีช่องทางติดต่อ
- ⚠️ ไม่มี website — แค่ email + เบอร์โทร
- ⚠️ ไม่มี case study, customer reference, testimonial
- ⚠️ ไม่มี pricing page / package comparison

### ❓ คำถาม

> 1. มีลูกค้าที่ใช้งาน NeuronHub แล้วกี่ราย? ขอ reference call ได้ไหม?
> 2. มี website / documentation public ไหม? (ถ้าไม่มี → onboarding ยังไง?)
> 3. ทีม develop NeuronHub มีกี่คน? Tech stack คืออะไร?

---

## 📊 Overall Assessment

| Criteria | คะแนน (1-5) | หมายเหตุ |
|---|---|---|
| **Presentation Quality** | 2 | 33% เป็น demo เดียว, ซ้ำซ้อน, ไม่มีตัวเลขชัดเจน |
| **Technical Depth** | 2 | ไม่มี latency, throughput, concurrency, accuracy benchmarks |
| **Competitive Moat** | 1 | ทุกฟีเจอร์ประกอบเองได้ด้วย open-source + Azure native |
| **Innovation** | 1 | n8n + Qdrant + Azure services — ไม่มี proprietary tech |
| **Value for Money** | 1 | 1.9M + 2×H100 เพื่อสิ่งที่ประกอบเองได้ที่ 80K/เดือน |
| **Enterprise Readiness** | 2 | ขาด cost tracking, audit, DR, sandbox, evaluation |

### 🟢 สิ่งที่ NeuronHub ทำได้ดี
- Text-to-SQL demo สวย (แต่ใช้ Northwind เล็กเกินไป)
- Guardian 2-layer inspection เป็นแนวคิดที่ดี
- Architecture diagram ครอบคลุม Azure ecosystem

### 🔴 สิ่งที่ NeuronHub ขาด
- **ตัวเลข** — ไม่มี benchmark, latency, accuracy, cost comparison
- **Proprietary Tech** — ไม่มีอะไรที่ทำเองไม่ได้
- **Enterprise Features** — audit log, cost chargeback, DR, sandbox
- **Customer Proof** — ไม่มี case study, testimonial, reference

### 💀 หน้าที่ไม่ควรมี / ควรรวม
- Page 5, 6, 7 → รวมเป็น 1 หน้า (screenshots Text-to-SQL)
- Page 9, 11 → รวมกับ 8, 10 (Guardian demo อยู่ในหน้าเดียวกัน)
- **รวม:** 12 หน้า → ควรเป็น 6-7 หน้าพอ

---

## 🧮 Scenario Analysis: ถ้าไม่เอา n8n + ไม่เอา Local LLM

> วิเคราะห์: ถ้าตัด n8n (ไม่เอา AI Agents) และตัด Local LLM (ไม่เอา Gemma/H100)
> เหลือแค่ **Gateway + RAG + Guardian + RBAC** — เปรียบเทียบ NeuronHub vs ทำเอง

### สิ่งที่จะหายไปถ้าไม่มี n8n

| ฟีเจอร์ | Impact | ใช้แทนอะไรได้ |
|---|---|---|
| AI Agents (Text-to-SQL, Calendar, Email, Drive) | ❌ หาย | Logic App, Azure Functions, custom code |
| Visual Workflow | ❌ หาย | เขียนโค้ดเอง หรือ Logic App Designer |
| MCP Server Integration | ❌ หาย | สร้าง MCP server แยกต่างหาก |

### สิ่งที่จะหายไปถ้าไม่มี Local LLM (2×H100)

| ฟีเจอร์ | Impact | ใช้แทนอะไรได้ |
|---|---|---|
| Guardian LLM Inspection | ❌ หาย | Azure AI Content Safety (~฿3,000/mo, 50ms latency) |
| Custom Model / Air-gap | ❌ หาย | Azure confidential inferencing (GPU + TEE) |
| Gemma on-premises | ❌ หาย | Azure OpenAI GPT-4o mini (pay-per-token) |

---

### 💰 Cost Breakdown: NeuronHub — แยกขา

| ชิ้นส่วน | Spec | Always-on Cost/เดือน | Cost/ปี |
|---|---|---|---|
| Gateway | 32 vCPU, 32GB, 1TB | ~฿35,000–55,000 | ~฿420,000–660,000 |
| n8n | 8 vCPU, 8GB, 500GB | ~฿12,000–18,000 | ~฿144,000–216,000 |
| Local LLM | 80 vCPU, 640GB, **2×H100** | ~฿200,000–350,000 | ~฿2,400,000–4,200,000 |
| **รวม (full stack)** | — | **~฿247,000–423,000/เดือน** | **~฿2,964,000–5,076,000/ปี** |

### 🧹 Scenario A: ตัด Local LLM (no H100)

| รายการ | ราคา/เดือน | ราคา/ปี |
|---|---|---|
| Gateway (32 vCPU) | ~฿35,000–55,000 | ~฿420,000–660,000 |
| n8n (8 vCPU) | ~฿12,000–18,000 | ~฿144,000–216,000 |
| **รวม** | **~฿47,000–73,000/เดือน** | **~฿564,000–876,000/ปี** |

> 💡 ตัด H100 = ประหยัด ~฿200K-350K/เดือน = ~฿2.4-4.2 ล้าน/ปี — **ลดเหลือ 20-25% ของราคาเดิม**

### 🧹 Scenario B: ตัดทั้ง n8n + Local LLM (เหลือแต่ Gateway)

| รายการ | ราคา/เดือน | ราคา/ปี |
|---|---|---|
| Gateway (32 vCPU) | ~฿35,000–55,000 | ~฿420,000–660,000 |
| **รวม** | **~฿35,000–55,000/เดือน** | **~฿420,000–660,000/ปี** |

> 💡 ตัดทั้ง n8n+H100 = เหลือ Gateway อย่างเดียว — **ลดเหลือ ~15% ของราคาเดิม**

---

### 🛠️ เทียบกับทำเอง (Self-Build)

#### Scenario A: ไม่มี Local LLM (มี Gateway + n8n)

| Component | Solution | Cost/เดือน |
|---|---|---|
| Gateway | LiteLLM บน Container Apps (2 vCPU, scale-to-zero) | ~฿2,000–5,000 |
| Chat UI | LibreChat/OpenWebUI บน Container Apps | ~฿3,000–8,000 |
| RAG | Azure AI Search (Basic) | ~฿8,000 |
| Content Safety | Azure AI Content Safety | ~฿3,000 |
| Agent Workflow | n8n บน Container Apps | ~฿3,000–8,000 |
| **รวม** | — | **~฿19,000–32,000/เดือน** |

> vs NeuronHub Scenario A: ~฿47,000–73,000/เดือน — **ทำเองถูกกว่า 60%**

#### Scenario B: ไม่มีทั้ง n8n + Local LLM (เหลือแต่ Gateway)

| Component | Solution | Cost/เดือน |
|---|---|---|
| Gateway | LiteLLM บน Container Apps (2 vCPU, scale-to-zero) | ~฿2,000–5,000 |
| Chat UI | LibreChat/OpenWebUI บน Container Apps | ~฿3,000–8,000 |
| RAG | Azure AI Search (Basic) | ~฿8,000 |
| Content Safety | Azure AI Content Safety | ~฿3,000 |
| **รวม** | — | **~฿16,000–24,000/เดือน** |

> vs NeuronHub Scenario B: ~฿35,000–55,000/เดือน — **ทำเองถูกกว่า ~55%**

---

### 📊 สรุปเปรียบเทียบทุก Scenario

| | Full Stack | Scenario A (no H100) | Scenario B (no H100 + no n8n) |
|---|---|---|---|
| **NeuronHub /เดือน** | ~฿247K–423K | ~฿47K–73K | ~฿35K–55K |
| **ทำเอง /เดือน** | ~฿50K–90K | ~฿19K–32K | ~฿16K–24K |
| **ส่วนต่าง /เดือน** | ~฿197K–333K | ~฿28K–41K | ~฿19K–31K |
| **ส่วนต่าง /ปี** | ~฿2.4–4.0M | ~฿336K–492K | ~฿228K–372K |
| **ทำเองถูกกว่า** | **~75-80%** | **~55-60%** | **~50-55%** |

---

### 🔑 Key Insight

1. **H100 คือตัวถ่วงใหญ่สุด** — ตัดออก = NeuronHub ราคาลด 80%
2. **n8n ราคาไม่ต่างกันมาก** — n8n VM ~฿15K/mo vs n8n Container Apps ~฿5K/mo → ส่วนต่างนิดเดียว
3. **Gateway 32 vCPU คือ Overkill** — LiteLLM ทำงานบน 2 vCPU ก็พอ → NeuronHub ใช้ 32 vCPU เพื่ออะไร?
4. **ถึงจะตัดทุกอย่างเหลือแค่ Gateway — NeuronHub ก็ยังแพงกว่าทำเอง 2 เท่า** เพราะใช้ VM แทน Container Apps

### 🎯 คำถามที่ต้องถาม IMC

> 1. ถ้าไม่เอา Local LLM — ราคาลดเหลือเท่าไหร่?
> 2. ถ้าไม่เอา n8n ด้วย — เหลือแต่ Gateway + RAG + Guardian — ราคาเท่าไหร่?
> 3. Gateway 32 vCPU — ใช้ทรัพยากรทำอะไรบ้าง? ทำไมไม่ใช้ Container Apps (scale-to-zero)?

---

## 🎯 Bottom Line

> NeuronHub ไม่ใช่ "แพลตฟอร์ม AI" — มันคือ **"n8n + Qdrant + Azure บน VM + regex guardian"** ที่ IMC ติดตั้งและตั้งราคาตาม hardware ที่ force-rent ให้

**ถ้า IMC ปรับเป็น:**
- ✅ ไม่บังคับ H100 — เลือก GPU ได้ตาม use case จริง
- ✅ Deploy บน Container Apps — scale-to-zero ลด cost 90%
- ✅ ราคาแยกส่วน — จ่ายเฉพาะส่วนที่ใช้
- ✅ มี enterprise feature จริง — audit, chargeback, DR

→ **อาจจะน่าสนใจ** แต่ ณ ตอนนี้ — **ข้อเสนอไม่สมเหตุสมผลกับราคา**
