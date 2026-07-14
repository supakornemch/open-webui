# NeuronHub Platform Review — คำถาม Vendor + Feature Gap Analysis

> **วันที่:** 2 กรกฎาคม 2569
> **ผู้วิเคราะห์:** ทีม EnterpriseChat
> **วัตถุประสงค์:** ใช้ประกอบการตัดสินใจจัดซื้อ NeuronHub และใช้ต่อรองกับ Vendor (IMC Outsourcing)

---

## Part 1: คำถามที่ต้องถาม Vendor

### 1. 💰 ราคา / License / Commercial Terms

| # | คำถาม | ทำไมต้องถาม |
|---|---|---|
| 1.1 | **1.9 ล้านรวมอะไรบ้าง?** ขอ Breakdown แยกเป็นค่า Hardware, License, ติดตั้ง, Support | ต้องรู้ว่าแต่ละส่วนราคาเท่าไหร่ จะได้เปรียบเทียบกับทำเองได้ตรงจุด |
| 1.2 | **Year 2+ จ่ายเท่าไหร่?** Hardware ต่ออายุ? License ต่ออายุ? Support ต่ออายุ? | Year 1 อาจตั้งราคาถูกเพื่อปิดงาน แต่ Year 2+ อาจแพงกว่ามาก — ขอ quote 3 ปี |
| 1.3 | **Hardware เป็น Reserved Instance หรือ On-Demand?** ถ้า Reserved — 1 ปี หรือ 3 ปี? | On-demand แพงกว่า Reserved ~40% — ต้องรู้ว่า cost structure เป็นยังไง |
| 1.4 | **Azure OpenAI token cost รวมในราคาหรือแยก?** | ถ้าแยก — งบประมาณต้องบวกเพิ่มอีก ไม่ใช่ 1.9M จบ |
| 1.5 | **มีค่าใช้จ่ายแอบแฝงไหม?** เช่น เพิ่ม user, เพิ่ม storage, เพิ่ม model, consulting เพิ่มเติม | ป้องกัน budget overrun ทีหลัง |

---

### 2. 🛡️ SLA / Support / Maintenance

| # | คำถาม | ทำไมต้องถาม |
|---|---|---|
| 2.1 | **Uptime Guarantee เท่าไหร่?** 99.5%? 99.9%? 99.99%? มี SLA credit ไหมถ้าไม่ถึง? | Azure AI Foundry ให้ 99.9% — NeuronHub ต้องไม่ต่ำกว่านี้ |
| 2.2 | **Response Time แจ้งปัญหา?** Severity 1 (ระบบล่ม) ตอบภายในกี่นาที? Severity 2/3/4? | Enterprise ต้องการ response time < 30 นาทีสำหรับ critical |
| 2.3 | **Root Cause Analysis (RCA)?** ถ้าระบบล่ม — ส่ง RCA ภายในกี่วัน? | Compliance & audit requirement |
| 2.4 | **Patch/Update จัดการยังไง?** แจ้งล่วงหน้ากี่วัน? มี maintenance window? ทำ outside business hours? | ระบบต้องไม่ downtime ระหว่างวันทำงาน |
| 2.5 | **Support Team อยู่ที่ไหน?** คนไทยหรือต่างประเทศ? ภาษาไทย/อังกฤษ? เวลาทำการ? | ถ้าคนนอก — response time ช่วงกลางคืนอาจช้า |

---

### 3. 🔒 Security / Compliance

| # | คำถาม | ทำไมต้องถาม |
|---|---|---|
| 3.1 | **Data Encryption** — At rest (Azure Disk Encryption? Customer-managed key?) และ In transit (TLS 1.3?)? | PDPA compliance — ข้อมูลส่วนบุคคลต้องเข้ารหัส |
| 3.2 | **Data Residency** — ข้อมูลทั้งหมดอยู่ใน Azure Thailand Region (Southeast Asia)? ออกนอก region ไหม? | กฎหมาย PDPA — cross-border data transfer ต้องแจ้ง |
| 3.3 | **PII Detection** — Guardian middleware ดัก PII (เลขบัตร ปชช., เบอร์โทร, email) ได้ไหม? แสดงผลเป็น masked? | PDPA — ต้องป้องกันข้อมูลส่วนบุคคลรั่วไหลผ่าน LLM |
| 3.4 | **Who has access to our data?** — ทีม IMC เข้าถึง log/ข้อมูล/โมเดลของเราได้ไหม? | Data privacy — vendor ต้องไม่มีสิทธิ์อ่านข้อมูล |
| 3.5 | **Penetration Test Report** — มีผล pentest ล่าสุดไหม? ขอดู executive summary ได้ไหม? | Security due diligence — platform ต้องผ่านการทดสอบ |
| 3.6 | **Authentication** — Entra ID integration รองรับ MFA, Conditional Access, PIM ไหม? | ป้องกัน unauthorized access |

---

### 4. 📈 Scalability / Performance

| # | คำถาม | ทำไมต้องถาม |
|---|---|---|
| 4.1 | **Concurrent Users** — รับได้กี่ concurrent users? คอขวดอยู่ที่ตรงไหน? | วางแผน rollout — 100 users vs 1,000 users |
| 4.2 | **Auto-Scale** — Gateway Scale-out ได้ไหม? Local LLM Scale-out ได้ไหม? | Peak load (ต้นเดือน/สิ้นเดือน) ระบบต้องไม่ล่ม |
| 4.3 | **Latency SLA** — Local LLM (Gemma) ตอบกลับภายในกี่วินาที? Gateway overhead เท่าไหร่? | User experience — ถ้าช้ากว่า 5 วิ user จะไม่ใช้ |
| 4.4 | **Rate Limiting** — ตั้ง limit per user / per department ได้ไหม? Over-limit ทำยังไง (queue/reject)? | ป้องกัน abuse + จัดการต้นทุน token |

---

### 5. 🤖 Local LLM / Hardware Justification

| # | คำถาม | ทำไมต้องถาม |
|---|---|---|
| 5.1 | **Gemma4 — รุ่นไหน?** Gemma 3 27B? หรือรุ่นอื่น? Infer อย่างเดียวหรือ fine-tune? | Gemma 3 27B รันบน T4 ฟรีก็ได้ — จ่าย H100 เพื่ออะไร? |
| 5.2 | **2× H100 จำเป็นจริงหรือ?** Benchmark vs A100/A10? Throughput (tokens/sec) เท่าไหร่? | 2×H100 = ฿5-6 แสน/เดือน — ถ้าไม่จำเป็นคือ waste |
| 5.3 | **Quantization** — รองรับ GGUF/AWQ/GPTQ? ใช้ความละเอียดเท่าไหร่ (8-bit/4-bit)? | ลด memory footprint → ใช้ GPU ถูกลงได้ |
| 5.4 | **Model Serving** — ใช้ vLLM/TGI/Ollama? Concurrent requests ได้กี่ requests? | Ollama เหมาะ dev ไม่ใช่ production → ชอบ vLLM มากกว่า |
| 5.5 | **Fallback** — ถ้า Local LLM ล่ม Auto-fallback ไป Azure OpenAI ไหม? | High availability — single point of failure |

---

### 6. 🚪 Exit Plan / Data Portability

| # | คำถาม | ทำไมต้องถาม |
|---|---|---|
| 6.1 | **ถ้าเลิกใช้ — ข้อมูล/โมเดล/prompt library เอากลับมาได้ไหม?** Format อะไร? มีค่าใช้จ่ายเพิ่มไหม? | ป้องกัน vendor lock-in |
| 6.2 | **Migration Support** — IMC ช่วย migrate ข้อมูลไป platform อื่นไหม? คิดเงินเท่าไหร่? | Smooth transition |
| 6.3 | **Notice Period** — ยกเลิกสัญญาต้องแจ้งล่วงหน้ากี่เดือน? | ช่วงทดลอง 1 ปี → ถ้าไม่เวิร์คจะออกยังไง |
| 6.4 | **Custom Code/Workflow** — n8n workflow ที่เราสร้างไว้ export เป็น JSON ได้ไหม? | n8n workflow ต้องใช้ต่อได้แม้ไม่มี NeuronHub |

---

## Part 2: สิ่งที่ NeuronHub ควรมีเพิ่มเติม

> 🔴 = Must Have — ขาดไม่ได้ / 🟡 = Should Have — ได้เปรียบคู่แข่ง / 🟢 = Nice to Have — สมบูรณ์แบบ

### 🔴 Must Have

| # | ฟีเจอร์ | รายละเอียด | สถานะใน NeuronHub |
|---|---|---|---|
| M1 | **Cost Tracking & Chargeback** | แยก bill ราย department, team, project — รู้ว่าใครใช้กี่ token กี่บาท ตั้ง budget cap ได้ | ❓ ไม่เห็นใน presentation |
| M2 | **Comprehensive Audit Log** | ใครถามอะไร เวลาไหน ได้คำตอบอะไร token usage, model, latency — export ได้ | ❓ Guardian มีแค่ content filter ไม่ใช่ audit |
| M3 | **Model Fallback / Circuit Breaker** | GPT ล่ม → auto switch Claude → auto switch Local LLM ตาม priority | ❌ ไม่มีใน architecture diagram |
| M4 | **API Key Rotation** | หมุนเวียน API key อัตโนมัติ แจ้งก่อนหมดอายุ — ไม่หลุดเพราะ key หมดอายุ | ❓ ไม่เห็น |
| M5 | **Data Retention Policy** | ตั้งอายุข้อมูล — log เก็บกี่วัน? conversation เก็บกี่วัน? auto-delete? | ❌ ไม่มี — เสี่ยง PDPA |

### 🟡 Should Have

| # | ฟีเจอร์ | รายละเอียด | ประโยชน์ |
|---|---|---|---|
| S1 | **Semantic Caching** | คำถามที่ความหมายเหมือนกัน → ตอบจาก cache ไม่เรียก LLM ซ้ำ | ลด token cost 20-40% |
| S2 | **A/B Prompt Testing** | เทียบ prompt 2 เวอร์ชั่น — วัด accuracy, latency, cost → เลือกอันที่ดีกว่า | Continuous improvement |
| S3 | **Prompt Versioning (Git-like)** | เก็บประวัติ prompt ทุกครั้งที่แก้ — diff view, rollback, approve ก่อน publish | ป้องกัน prompt regression |
| S4 | **Sandbox/Staging Environment** | environment แยกสำหรับทดสอบก่อน deploy production | ลด risk ทดสอบ prompt ใหม่ |
| S5 | **Real-time Usage Dashboard** | เห็น live — concurrent users, tokens/min, latency, error rate, top users | Operations visibility |
| S6 | **Guardrails Policy as Code** | ตั้ง content filter เป็น YAML/JSON — version control ได้, review ได้ | Audit + compliance |
| S7 | **Evaluation & Benchmark** | รัน eval dataset เทียบ accuracy, relevancy, hallucination ระหว่าง models | รู้ว่า model ไหนดีสุดสำหรับ use case เรา |
| S8 | **Webhook / Event Stream** | ส่ง event (chat started, token exceeded, error) ไปยังระบบอื่น | Integrate กับ monitoring/dashboard ที่มีอยู่ |

### 🟢 Nice to Have

| # | ฟีเจอร์ | รายละเอียด |
|---|---|---|
| N1 | **API Versioning** | รองรับ API หลายเวอร์ชั่นพร้อมกัน ไม่ break app ที่ใช้อยู่ |
| N2 | **Multi-Tenancy** | แยก tenant แบบ logical partition — HR กับ Finance ใช้ platform เดียวกันแต่แยก data |
| N3 | **Custom Plugin/Extension** | ให้ลูกค้าเขียน plugin เอง — custom guard, custom model, custom UI component |
| N4 | **Scheduled Prompt Execution** | ตั้งเวลา run prompt อัตโนมัติ — รายงานสรุปทุกเช้า, แจ้งเตือนเมื่อถึง threshold |
| N5 | **Conversation Export** | ส่งออกบทสนทนาเป็น PDF/JSON/CSV — ใช้ทำ report หรือแนบ audit |
| N6 | **Feedback Loop** | User ให้คะแนนคำตอบ (👍/👎) → เก็บเป็น dataset → ใช้ปรับ prompt |
| N7 | **SSO / SAML** | นอกจาก Entra ID — รองรับ SAML สำหรับ partner/外部 ที่ไม่ได้ใช้ Entra |

---

## Part 3: คำถามเชิง Architecture ที่ควรถาม Team IMC

| # | คำถาม | เจาะลึก |
|---|---|---|
| A1 | **Gateway จริง ๆ คืออะไร?** Custom code? หรือ wrap nginx/Envoy/LiteLLM? Source code ให้ดูได้ไหม? | ถ้าแค่ LiteLLM + config → ไม่ต้องซื้อ |
| A2 | **Qdrant จำเป็นไหม?** Azure AI Search ทำ vector+hybrid search ได้ในตัว — Qdrant เพิ่ม overhead? | ถ้าไม่ได้ใช้ Qdrant จริง → เอาเงินไปอัพเกรด AI Search ดีกว่า |
| A3 | **n8n ใช้ Community Edition หรือ Enterprise?** ถ้า Community — เราลงเองฟรี | n8n Enterprise มี SSO, audit, RBAC — ถ้า Community ก็ไม่ต่างจากลงเอง |
| A4 | **Guardian middleware** — ใช้ LLM ตัวไหน inspect? ใช้ GPT-4? latency เพิ่มเท่าไหร่? | ถ้าใช้ GPT-4 → cost ×2 ทุก request + latency เพิ่ม 2-5 วิ |
| A5 | **มีการทำ Load Test ไหม?** ผล 100/500/1,000 concurrent users — แชร์ report ได้ไหม? | รู้ขีดจำกัดก่อนใช้งานจริง |

---

## Summary: 3 คำถามเด็ดที่ต้องได้คำตอบก่อนเซ็นสัญญา

1. **"2× H100 จำเป็นจริงไหม? ขอดู benchmark เทียบกับ A100 สำหรับ Gemma infer อย่างเดียว"**
2. **"Year 2, 3, 4 — แต่ละปีจ่ายเพิ่มเท่าไหร่? ขอ TCO 4 ปี"**
3. **"ถ้าเลิกใช้ — เราจะเอาข้อมูล/prompt/n8n workflow กลับมาทั้งหมดได้ภายในกี่วัน? มีค่าใช้จ่ายไหม?"**

> ⚠️ **ถ้า IMC ไม่สามารถตอบ 3 คำถามนี้ได้ชัดเจน — ไม่ควรเซ็นสัญญา**

---

*Document version: 1.0 — Prepared for internal evaluation*
