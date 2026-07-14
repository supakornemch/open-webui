# ADR 0005: LLM Backend — Hybrid (Azure OpenAI + Ollama)

## Status
Accepted

## Context
ทั้ง n8n (AI nodes) และ Open WebUI ต้องการ LLM backend
ไม่ตายตัว — ต้องรองรับทั้ง cloud และ self-hosted models

## Decision
ออกแบบ **Hybrid LLM Backend** — รองรับทั้ง Azure OpenAI Service และ Ollama พร้อมกัน
- POC: เริ่มจาก Azure OpenAI Service เป็นหลัก
- Scale up: เพิ่ม Ollama บน GPU node pool สำหรับ local/small models

## Consequences
- ✅ ยืดหยุ่น — เลือกใช้ model ที่เหมาะสมกับ task
- ✅ ไม่ต้อง GPU ตั้งแต่เริ่ม — ลดต้นทุน POC
- ✅ Open WebUI รองรับ multi-model conversations อยู่แล้ว
- ⚠️ ต้องเตรียม GPU node pool infrastructure ไว้ (SKU, sizing)
- ⚠️ Configuration ซับซ้อนกว่า — ต้องจัดการ model routing
