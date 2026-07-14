# LLM Chat Use Cases — อุตสาหกรรมเครื่องดื่ม

> สรุป Use Case การใช้ LLM / Generative AI ในธุรกิจเครื่องดื่มระดับโลก  
> สำหรับ Haadthip — อ้างอิงจากกรณีศึกษาของ Coca-Cola, PepsiCo, Nestlé, Southern Glazer's, Breakthru Beverage และอื่นๆ  
> ข้อมูล ณ กรกฎาคม 2026

---

## สารบัญ

1. [ภาพรวม](#ภาพรวม)
2. [Sales & Distribution (การขายและจัดจำหน่าย)](#1-sales--distribution-การขายและจัดจำหน่าย)
3. [Customer Service (บริการลูกค้า)](#2-customer-service-บริการลูกค้า)
4. [Marketing & Consumer Engagement (การตลาด)](#3-marketing--consumer-engagement-การตลาด)
5. [Supply Chain & Operations (ซัพพลายเชน)](#4-supply-chain--operations-ซัพพลายเชน)
6. [HR & Internal Knowledge (ทรัพยากรบุคคลและองค์ความรู้)](#5-hr--internal-knowledge-ทรัพยากรบุคคลและองค์ความรู้)
7. [Business Intelligence (วิเคราะห์ข้อมูลธุรกิจ)](#6-business-intelligence-วิเคราะห์ข้อมูลธุรกิจ)
8. [Product Innovation (นวัตกรรมสินค้า)](#7-product-innovation-นวัตกรรมสินค้า)
9. [Thailand & ASEAN Examples](#8-ตัวอย่างในไทยและอาเซียน)
10. [Strategic Roadmap สำหรับ Haadthip](#strategic-roadmap-สำหรับ-haadthip)
11. [อ้างอิง](#อ้างอิง)

---

## ภาพรวม

บริษัทเครื่องดื่มและผู้จัดจำหน่ายชั้นนำทั่วโลกกำลังใช้ LLM (Large Language Models) และ Generative AI ในหลากหลายฟังก์ชัน ตั้งแต่การขาย การตลาด ซัพพลายเชน ไปจนถึงงานภายในองค์กร โดยผลลัพธ์ที่วัดได้จริง เช่น:

| บริษัท | ผลลัพธ์เด่น |
|--------|------------|
| **Coca-Cola** | สร้าง content 10,000 ชิ้นใน 130+ ภาษา; engagement สูงขึ้น 20%; ผลิตเร็วกว่าเดิม 3 เท่า |
| **Choco** | ลด manual order entry 50%; เพิ่ม productivity ทีมขาย 2 เท่า |
| **Burnt (Ozai)** | 97% ของออเดอร์ดำเนินการโดย AI แบบ end-to-end ไม่ต้องใช้คน |
| **AnyMind (Evian Thailand)** | ยอดขาย Live Commerce เพิ่ม 3.5 เท่า; ลดต้นทุน 90% |
| **Southern Glazer's** | Digital touch ~70% ของยอดขายทั้งหมด |
| **HiBob** | 90%+ ของพนักงานใช้ ChatGPT Enterprise ทุกวัน |

---

## 1. Sales & Distribution (การขายและจัดจำหน่าย)

### 1.1 Automated Order Intake — รับออเดอร์อัตโนมัติ

**Pain Point:** ออเดอร์เข้ามาหลากหลายช่องทาง — โทรศัพท์, LINE/WhatsApp, อีเมล, ใบสั่งซื้อ, รูปถ่าย — พนักงานขายต้องเสียเวลาคีย์ข้อมูลเข้า ERP เอง

**How LLM helps:**
- LLM transcribe เสียง/ข้อความ → แปลงเป็น structured order
- จับคู่ชื่อสินค้าในแชทกับ SKU ในระบบ (เช่น "โค้กขวดเล็ก" → SKU 12345)
- สร้าง order โดยตรงใน ERP โดยไม่ต้องคีย์มือ

**Case Study — Choco OrderAgent**
- ให้บริการผู้จัดจำหน่าย **21,000+ ราย** ผู้ซื้อ **100,000+ ราย**
- ใช้ OpenAI API ประมวลผลคำสั่งซื้อจาก SMS, อีเมล, รูปภาพ, เอกสาร
- **ผลลัพธ์:** 8.8M+ ออเดอร์/ปี, manual entry ลดลง 50%, productivity ทีมขายเพิ่ม 2 เท่า
- Error rate ต่ำกว่า 1–5%

**Case Study — Burnt Ozai**
- AI agents ทำงานภายใน ERP เดิมโดยไม่ต้องเปลี่ยนระบบ
- **97% ของออเดอร์ดำเนินการ end-to-end โดยไม่มีคน**
- พนักงาน order entry 90% เปลี่ยนบทบาทไปทำงานขายแทน

**Case Study — CJ Freshway (เกาหลีใต้)**
- ระบบสั่งซื้อด้วยภาษาธรรมชาติ: "เพิ่มรายการเดียวกับเมื่อวาน"
- AI จับคู่สินค้า, spec, ปริมาณ อัตโนมัติ

---

### 1.2 AI Sales Rep Assistant — ผู้ช่วยพนักงานขาย

**Pain Point:** พนักงานขายมีเวลาขายจริงแค่ ~30% ที่เหลือหมดไปกับงาน admin — ดึงข้อมูลลูกค้า, เช็คสต็อก, เขียน follow-up, บันทึก call notes

**How LLM helps:**
- ผู้ช่วย conversational ใน CRM ถาม-ตอบด้วยภาษาธรรมชาติ
- ดึงข้อมูลลูกค้า, ยอดขายย้อนหลัง, สินค้าที่ควรแนะนำ
- สร้าง draft อีเมล/ข้อความติดตามลูกค้า
- บันทึกสรุปการเข้าพบอัตโนมัติ

**Case Study — Proton.ai Pronto**
- AI assistant ฝังใน CRM สำหรับ distributor sales reps
- ความสามารถ:
  - "ดึงหมวดสินค้าที่ลูกค้ารายนี้ซื้อมากที่สุด"
  - "เช็คสินค้าที่ลูกค้ายังไม่เคยซื้อแต่ร้านอื่นซื้อ"
  - "แนะนำสินค้าทดแทนถ้าของหมด"
  - "ร่างอีเมลแนะนำสินค้า"
  - "บันทึก call notes และ next steps"

---

### 1.3 Intelligent Product Recommendations — แนะนำสินค้าอัจฉริยะ

**Pain Point:** Distributor รายหนึ่งอาจมี 15,000–20,000 SKUs พนักงานขายมีเวลาเจอลูกค้าแค่ 15–30 นาที ไม่มีใครรู้จักทุกสินค้า

**How LLM helps:**
- AI วิเคราะห์ transaction history, inventory, trends → แนะนำสินค้าเฉพาะแต่ละร้าน
- คำนึงถึงข้อจำกัด (สินค้า limited edition, เขตจำหน่าย, โควต้า)

**Case Study — Southern Glazer's Wine & Spirits**
- ผู้จัดจำหน่ายแอลกอฮอล์รายใหญ่สุดในสหรัฐฯ
- AI ให้ insights **ระดับ SKU เฉพาะแต่ละร้านค้า**
- วิเคราะห์: transaction history, เมนู, shelf composition, inventory, ข้อจำกัดทางกฎหมาย
- ปรัชญา: **AI aid, not replace** — AI ให้ insights; พนักงานใช้ local knowledge เสริม
- Digital touch **~70% ของยอดขายทั้งหมด**

---

### 1.4 B2B E-Commerce Chatbot — แชทบอทสั่งซื้อออนไลน์

**Pain Point:** ลูกค้า (ร้านค้า, ร้านอาหาร, โรงแรม) ต้องการสั่งซื้อนอกเวลาทำการ

**How LLM helps:**
- Chatbot 24/7 บนพอร์ทัล B2B
- ค้นหาสินค้า, แนะนำสินค้า, เช็คสต็อก, สร้างออเดอร์
- เสนอ upsell/cross-sell เมื่อมีสินค้าใกล้หมดอายุหรือโปรโมชั่น

**Case Study — Breakthru Beverage Group**
- Distributor มูลค่า **$8.6 พันล้าน**
- ฝัง AI chatbot ใน B2B e-commerce "Breakthru Now"
- เป้าหมาย: **$700 ล้าน** ผ่านช่องทางดิจิทัล
- วางแผนรองรับ **agentic AI** ที่ตัดสินใจและเรียนรู้ได้เอง

**Case Study — Choco VoiceAgent**
- ใช้ OpenAI Realtime API
- **รับสาย, รับออเดอร์, ตอบคำถามสินค้า** ได้ทุกภาษา 24/7
- เช็คสต็อก real-time; แนะนำสินค้าทดแทนถ้าของหมด
- แจ้งโปรโมชั่นสินค้าใกล้หมดอายุ → ลด food waste

---

### 1.5 Image-Based Product Lookup — ค้นหาสินค้าจากรูปภาพ

**Pain Point:** ลูกค้าขอสินค้าที่ยังไม่มีใน catalog — ต้องค้นหาด้วยมือ ส่งอีเมลไปมา

**How LLM helps:**
- ลูกค้าถ่ายรูปขวด/ฉลาก → AI ระบุสินค้า
- ค้นหาใน catalog ก่อน → ถ้าไม่มี เสนอทางเลือก → ถ้าลูกค้ายืนยัน สร้าง case จัดซื้ออัตโนมัติ

**Case Study — Evenica B2B Product Request Agent**
- AI conversational agent + image recognition
- Unified workflow: catalog search → alternative suggestion → image recognition → auto case creation

---

## 2. Customer Service (บริการลูกค้า)

### 2.1 24/7 Voice Agent — รับสายออเดอร์นอกเวลา

**(ดูรายละเอียดเพิ่มเติมที่ 1.1 และ 1.4 — Choco VoiceAgent)**

### 2.2 B2B Consultation Chatbot — ที่ปรึกษาด้านสินค้า

**Case Study — Wollenhaupt TEASY Chatbot**
- AI chatbot สำหรับลูกค้า wholesale และ gastronomy
- ตอบคำถาม: ข้อมูลผลิตภัณฑ์, วิธีชง, รสชาติ, แหล่งที่มา, ไอเดียสูตร
- ให้บริการ 24/7 นอกเวลาทำการปกติ

### 2.3 Consumer-Facing AI Experiences — สร้างประสบการณ์ผู้บริโภค

**Case Study — Coca-Cola "Talk to Santa"**
- Interactive chatbot 26 ภาษา
- รวม Azure speech-to-text + GPT-4 + multimodal model
- ผู้ใช้ใช้เวลาเฉลี่ย **8 นาที 20 วินาที**  interacting
- เก็บ first-party data และ consent

**Case Study — PepsiCo Desafi.A Pepsi**
- Pepsi Challenge ยุคใหม่ ใช้ AI multisensory
- วัด preference ผ่าน: เสียง (tone, word choice), สีหน้า (facial emotion detection), คลื่นสมอง (EEG)
- นำร่องที่ Costa Rica กุมภาพันธ์ 2025

---

## 3. Marketing & Consumer Engagement (การตลาด)

### 3.1 Content Production at Scale — สร้างคอนเทนต์จำนวนมาก

**Case Study — Coca-Cola**
- สร้าง **20 AI-generated master assets**
- AI สร้าง **10,000 localized variations** 130+ ภาษา
- Consumer engagement สูงขึ้น **20%**
- ผลิตเร็วกว่าเดิม **3 เท่า**
- สัญญา **$1.1 พันล้าน 5 ปี** กับ Microsoft สำหรับ Azure OpenAI Service

### 3.2 Hyper-Personalized Marketing — การตลาดเฉพาะบุคคล

**Case Study — PepsiCo**
- GenAI เร่ง consumer insights → hyper-personalized campaigns
- AI-powered ad testing (Zappi Amplify) → creative effectiveness เพิ่ม **30%**

### 3.3 AI Live Commerce — ไลฟ์สดขายของด้วย AI

**Case Study — AnyMind x Evian (Thailand, 2024)**
- ใช้ AI avatar ไลฟ์สดบน Shopee Thailand
- **ผลลัพธ์ (9 สัปดาห์):**
  - ยอดขาย Live Commerce เพิ่ม **3.5 เท่า**
  - GenAI sessions ทำยอดขาย >80% ของทั้งหมด
  - ลดต้นทุนปฏิบัติการ **สูงสุด 90%**
  - จาก 865 ชั่วโมง streaming, 820 ชั่วโมงใช้ AI (human เฉพาะ peak hours)

---

## 4. Supply Chain & Operations (ซัพพลายเชน)

### 4.1 Demand Forecasting & Replenishment — พยากรณ์ความต้องการ

**Case Study — Coca-Cola**
- AI algorithm ผสม GenAI + traditional AI
- วิเคราะห์: historical sales + weather data + geolocation signals
- ส่งข้อความ personalized ทาง **WhatsApp** บอกร้านค้าว่าควรเติมสต็อกอะไร เมื่อไหร่
- **ยอดขายเพิ่ม 5–20% ต่อเดือน** ใน ~1,000 outlets
- กำลังขยายทั่วโลก

### 4.2 Fulfillment Planning — วางแผนการจัดส่ง

**Case Study — Nestlé**
- GenAI สร้าง fulfillment plans สำหรับ distributors และ retail customers
- AI วิเคราะห์ end-to-end: ส่วนลด, market share, competitive dynamics → pricing models
- **~100,000 พนักงาน** ใช้ Microsoft Copilot ทุกเดือน
- กำลังพัฒนา agentic AI: retailers' agents ↔ Nestlé's agents ทำงานร่วมกัน

### 4.3 Quality Control — ควบคุมคุณภาพ

**Case Study — Albertsons + Google Cloud Gemini Vision AI**
- AI ตรวจสอบคุณภาพผักผลไม้สดที่ distribution centers
- ประเมินสม่ำเสมอกว่า inspector ที่เป็นมนุษย์
- ตัดสินใจเร็วขึ้น → สินค้าถึงร้านเร็วขึ้น

### 4.4 Digital Twins & Smart Manufacturing

**Case Study — PepsiCo**
- Digital twins + agentic AI ใน manufacturing
- Physical AI: autonomous robots, smart factory systems

**Case Study — Thongpanom Fermentation House (ไทย, 2025)**
- Smart Brewery ระบบ IoT + sensors + data analytics + AI
- ควบคุมคุณภาพการหมัก; รักษามาตรฐานการผลิต

---

## 5. HR & Internal Knowledge (ทรัพยากรบุคคลและองค์ความรู้)

### 5.1 HR Policy Chatbot — ถาม-ตอบนโยบายบริษัท

**Pain Point:** นโยบายกระจัดกระจาย — คู่มือพนักงาน, สิทธิประโยชน์, ระเบียบการลา, IT policy — พนักงานไม่รู้จะถามใคร

**How LLM helps:**
- RAG-based chatbot อ่านเอกสารนโยบายทั้งหมด
- ตอบคำถามด้วยภาษาธรรมชาติ พร้อมอ้างอิง source
- ลด tickets ของ HR helpdesk ได้ถึง 70%

**Case Study — Coca-Cola Vietnam (2025)**
- GenAI conversational interface สำหรับ HR
- สร้างบน Microsoft Azure OpenAI Service
- พนักงานถามนโยบายที่กระจัดกระจายได้จากที่เดียว

**Case Study — AWS Marketplace HR Buddy**
- Agentic RAG assistant ตอบคำถาม "สั่ง laptop ยังไง?" "มีวันลากี่วัน?"
- เรียกข้อมูลจาก HRIS APIs
- อ้างอิง clause ในนโยบายแบบเป๊ะๆ
- ลด helpdesk tickets **สูงสุด 70%**

---

### 5.2 Internal Enterprise Knowledge Base — ฐานความรู้องค์กร

**Pain Point:** เอกสารภายใน (SOP, คู่มือการทำงาน, เอกสาร SAP, รายงาน) ถูกเก็บแบบกระจัดกระจาย — พนักงานหาไม่เจอ, ไม่รู้ว่ามีอยู่, หรือใช้เวลาหานาน 10–30 นาที

**How LLM helps:**
- RAG (Retrieval-Augmented Generation) บนเอกสารภายใน
- พนักงานถามด้วยภาษาธรรมชาติ → ได้คำตอบพร้อม citation
- Role-based access control — แต่ละแผนกเห็นเอกสารตามสิทธิ์

**Case Study — Coca-Cola Enterprise ChatGPT**
- พนักงานใช้ internal ChatGPT-like tool
- ค้นหาข้อมูลจาก proprietary company data
- ทำหน้าที่เป็น enterprise knowledge assistant

**Case Study — PepsiCo Ada & PepGenX**
- Internal GenAI-powered knowledge engines
- "Answer engines" สำหรับพนักงานทั่วองค์กร

**Case Study — HiBob**
- HR tech company สร้าง **2,500+ GPTs ทดลอง** (200 ขึ้น production)
- ใช้สำหรับ: meeting prep, upselling, onboarding transcript summarization, SEO, roadmap analysis
- **พนักงาน 90%+** ใช้ ChatGPT Enterprise ทุกวัน

---

### 5.3 Employee Onboarding — รับพนักงานใหม่

**How LLM helps:**
- AI agent สร้าง personalized onboarding plan ให้พนักงานใหม่แต่ละคน
- ตอบคำถาม FAQ โดยอัตโนมัติ
- Auto-enroll เข้า LMS courses ตามตำแหน่ง
- Monitor progress ตลอดช่วง onboarding

**Case Study — Turing**
- LLM วิเคราะห์ onboarding videos → สร้าง interactive learning modules อัตโนมัติ
- Onboard 5,000+ คนในครึ่งปี
- ลดเวลาเตรียมโปรแกรมจาก **สัปดาห์ → 3 ชั่วโมง**

**Case Study — Microsoft Power Platform**
- Onboarding agent ดึงข้อมูลจาก HRIS (Workday, SAP SuccessFactors)
- สร้าง learning plan, ตอบ FAQ, monitor progress

---

### 5.4 Training Content Creation — สร้างเนื้อหาอบรม

**How LLM helps:**
- อัปโหลดเอกสาร (PDF, DOCX, PPTX) → AI สร้าง SCORM course สำหรับ LMS อัตโนมัติ
- สร้าง quiz, แบบทดสอบ
- Localization — สร้าง training หลายภาษาด้วย synthetic voice

**Case Study — Multi-Agent RAG → SCORM (Frontiers in AI, 2026)**
- Pipeline อัตโนมัติ: ingest เอกสารองค์กร → LLM agent ออกแบบหลักสูตร → สร้างบทเรียน → แพ็คเป็น SCORM 1.2
- Deploy ได้กับทุก LMS

**Case Study — Uniridge GPT-4 HR Chatbot**
- GPT-4 + OneDrive + Office 365 + Azure AD + SSO
- ลดเวลา HR team **6%**
- พนักงานใหม่สอบผ่าน quiz รอบแรก **80%**

---

## 6. Business Intelligence (วิเคราะห์ข้อมูลธุรกิจ)

### 6.1 Conversational Analytics — ถาม-ตอบข้อมูลธุรกิจ

**Pain Point:** Reports แบบ static ถูกสร้างเป็นพันฉบับ แต่ไม่มีใครเปิดดู — ผู้บริหาร/พนักงานขาย ต้องการคำตอบเฉพาะหน้า แต่ต้องขอให้ทีม data analyst ดึงข้อมูลให้

**How LLM helps:**
- Text-to-SQL / natural language query บน data warehouse
- "ยอดขายภาคใต้ไตรมาสนี้เทียบกับปีที่แล้วเป็นยังไง?"
- "สินค้าไหน margin ลดลงมากที่สุด?"
- "ร้านค้าไหนที่ยอดขายตกลงติดต่อกัน 3 เดือน?"

**Case Study — Coca-Cola Vietnam Cooler Monitoring Chatbot (2025)**
- GenAI embedded monitoring system
- Sales reps + asset managers "dialog with data" ด้วย natural language
- ติดตาม cooler ROI, ระบุ outlets ที่ underperform
- ได้ actionable insights ผ่าน conversational interface เดียว

**Case Study — PepsiCo "Dialoguing with Data"**
- เปลี่ยนจาก static reports → conversational chatbots
- Business users ทุกฟังก์ชัน (supply chain, commercial, consumer) ถามด้วยภาษาธรรมชาติ
- เห็น traction สูงจาก business teams ที่ดึงระบบไปใช้เอง

**Case Study — The Wholesale Group Jake AI**
- Conversational AI สำหรับ wholesale members 255+ ราย
- ถาม: "อะไรทำให้ margin ของ frozen foods ลดลงไตรมาสนี้?"
- วิเคราะห์ market trends, ระบุ promotional opportunities, correlate sales patterns

---

## 7. Product Innovation (นวัตกรรมสินค้า)

### 7.1 AI Co-Created Products

**Case Study — Coca-Cola Y3000 Zero Sugar**
- รสชาติเกิดจากการใช้ generative AI วิเคราะห์ global taste trends
- วางตลาดในฐานะ "เครื่องดื่มแรกที่ co-created กับ AI"

### 7.2 Accelerated R&D

**Case Study — PepsiCo**
- GenAI เร่ง product development cycles
- ใช้ tools เช่น Tastewise สำหรับ trend forecasting
- Predictive modeling สำหรับ targeted health innovations

---

## 8. ตัวอย่างในไทยและอาเซียน

### 8.1 AnyMind x Evian — AI Live Commerce (2024)
- ผู้จัดจำหน่าย: Sino Pacific Trading (Evian)
- แพลตฟอร์ม: Shopee Thailand
- ยอดขายเพิ่ม 3.5 เท่า, ต้นทุนลด 90%

### 8.2 Coca-Cola ASEAN — GenAI Marketing (2024)
- ASEAN marketing head เรียก GenAI ว่า **"iPhone moment"**
- สัญญา $1.1B กับ Microsoft
- ทำ hyper-local campaigns ในตลาด APAC ที่หลากหลาย

### 8.3 Thongpanom Fermentation House — Smart Brewery (2025)
- KMUTT + Sato brewer
- IoT + AI ควบคุมการหมัก
- Smart Manufacturing ต้นแบบในไทย

### 8.4 Coca-Cola Vietnam — HR Chatbot + Cooler Monitoring (2025)
- 2 use cases ใน Vietnam:
  1. HR Policy Chatbot (Azure OpenAI)
  2. Cooler Productivity Chatbot (conversational analytics)

---

## Strategic Roadmap สำหรับ Haadthip

จากกรณีศึกษาทั้งหมด นี่คือ use cases ที่แนะนำสำหรับ Haadthip เรียงตามความพร้อมและผลกระทบ:

| Phase | Use Case | Impact | Complexity | ใช้ LLM |
|-------|----------|--------|------------|---------|
| **🚀 Phase 1** (Now) | **Internal Knowledge Base** — RAG บนเอกสารภายใน (SOP, HR, SAP manuals, product info) | 🔴🔴🔴🔴 High | 🟢🟢 Low | ✅ |
| **🚀 Phase 1** (Now) | **Sales Rep Assistant** — ถาม-ตอบข้อมูลลูกค้า, สินค้า, สต็อก ใน LINE/Web | 🔴🔴🔴🔴 High | 🟢🟢 Low | ✅ |
| **🟡 Phase 2** (3-6 mo) | **Automated Order Intake** — รับออเดอร์จาก LINE/โทรศัพท์ → เข้า ERP | 🔴🔴🔴🔴🔴 Very High | 🟡🟡🟡 Med | ✅ |
| **🟡 Phase 2** (3-6 mo) | **Conversational BI** — ผู้บริหารถามยอดขาย/แนวโน้มด้วยภาษาธรรมชาติ | 🔴🔴🔴 High | 🟡🟡🟡 Med | ✅ |
| **🟡 Phase 2** (3-6 mo) | **HR Onboarding Chatbot** — ตอบคำถามพนักงานใหม่ + สร้าง learning plan | 🔴🔴🔴 High | 🟢🟢 Low | ✅ |
| **🔵 Phase 3** (6-12 mo) | **B2B Ordering Chatbot** — ร้านค้าสั่งซื้อ 24/7 ผ่าน LINE OA | 🔴🔴🔴🔴🔴 Very High | 🟡🟡🟡 Med | ✅ |
| **🔵 Phase 3** (6-12 mo) | **Demand Forecasting** — AI พยากรณ์ + แจ้งเติมสต็อก | 🔴🔴🔴🔴 High | 🔴🔴🔴 High | ✅ |
| **🔵 Phase 3** (6-12 mo) | **Marketing Content AI** — สร้างคอนเทนต์ localized จำนวนมาก | 🔴🔴🔴 High | 🟡🟡🟡 Med | ✅ |

### สิ่งที่ Haadthip มีอยู่แล้ว (ณ ก.ค. 2026)

| Resource | รายละเอียด |
|----------|-----------|
| **Azure OpenAI** | gpt-5.4-nano, gpt-5.4-mini, gpt-5.4, gpt-5.2, text-embedding-3-large |
| **AI Search** | Standard tier, semantic + vector search, 2 indexes (haadthip-public-idx-v2, sap-docs-idx) |
| **Knowledge Base** | haadthip-kb + 2 knowledge sources (haadthip-ks, sap-docs-ks) |
| **Agentic Retrieval** | ทำงานแล้ว — query ภาษาไทย/อังกฤษ, ค้นหาข้าม index, ตอบจากเอกสารภายใน |
| **Open WebUI** | Deployed บน App Service, Entra ID SSO |
| **เอกสาร indexed** | 16+25 = 41 เอกสาร (general + SAP) |

### คำแนะนำขั้นต่อไป

1. **เปิดใช้ KB ใน Open WebUI ทันที** — ลงทะเบียน search endpoint เป็น Tool ใน Admin > Tools
   → พนักงานสามารถถามคำถามจากเอกสารภายในผ่านแชทได้ทันที
2. **ขยายเอกสารใน index** — เพิ่ม HR manuals, product catalogs, sales guides
3. **LINE Integration** — ให้พนักงานขายถามผ่าน LINE แทน webUI (ลด friction)
4. **สร้าง specialized assistants** — HR bot, Sales bot, SAP support bot (แยก persona)

---

## อ้างอิง

### Global Beverage Leaders
- Coca-Cola: [Fortune AIQ 50 (#6)](https://fortune.com/ranking/ai-innovators/), [Microsoft $1.1B partnership](https://news.microsoft.com), [Coca-Cola Vietnam HR Chatbot](https://news.microsoft.com/apac)
- PepsiCo: [Enterprise Data Foundation](https://www.pepsico.com), [Salesforce Agentforce](https://www.salesforce.com), [Desafi.A Pepsi](https://www.pepsico.com)
- Nestlé: [GenAI Supply Chain](https://www.nestle.com), [~100K monthly Copilot users](https://www.nestle.com)
- Southern Glazer's Wine & Spirits: [AI Product Recommendations](https://www.southernglazers.com)
- Breakthru Beverage Group: [$700M digital channel](https://www.breakthrubev.com)

### Distribution & Supply Chain
- Choco: [OrderAgent & VoiceAgent](https://www.choco.com)
- Burnt Ozai: [Y Combinator](https://www.ycombinator.com)
- CJ Freshway: [AI Ordering Agent](https://www.cjfreshway.com)
- Albertsons + Google Cloud: [Vision AI Quality Control](https://cloud.google.com)
- Proton.ai Pronto: [AI Sales Rep Assistant](https://www.proton.ai)

### Thailand & ASEAN
- AnyMind x Evian Thailand: [AI Live Commerce](https://www.anymindgroup.com)
- Coca-Cola ASEAN: [GenAI "iPhone moment"](https://www.coca-colacompany.com)
- Thongpanom Fermentation House: [Smart Brewery x KMUTT](https://www.kmutt.ac.th)

### HR & Employee Experience
- Microsoft Power Platform: [Onboarding Agent](https://learn.microsoft.com/en-za/power-platform/architecture/solution-ideas/onboarding-agent)
- Turing: [HR Workflows AI](https://workspace.google.com/blog/ai-and-machine-learning/turing-transforming-hr-workflows-ai)
- HiBob: [2,500+ GPTs, 90%+ adoption](https://openai.com/index/hibob/)
- Uniridge: [GPT-4 HR Chatbot](https://techreviewer.co)
- Frontiers in AI: [Multi-Agent RAG → SCORM (2026)](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1834985/full)
- AWS Marketplace: [Agentic RAG HR Buddy](https://aws.amazon.com/marketplace/pp/prodview-6i6mf2fwh7meq)

---

> **Last updated:** 2026-07-05  
> **Author:** ZCode Agent — research from global beverage + distribution LLM use cases
