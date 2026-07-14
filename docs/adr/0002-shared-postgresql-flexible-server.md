# ADR 0002: Database — Shared Azure Database for PostgreSQL Flexible Server

## Status
Accepted

## Context
n8n และ Open WebUI ทั้งสองต้องการ database:
- n8n: PostgreSQL (required สำหรับ production)
- Open WebUI: PostgreSQL หรือ SQLite

ต้องตัดสินใจว่าจะแยกหรือรวม database instance

## Decision
ใช้ **Azure Database for PostgreSQL Flexible Server ใช้ร่วมกัน** — แยก database name แยก user ใน instance เดียวกัน

## Consequences
- ✅ ลดต้นทุน — จ่าย instance เดียว
- ✅ ลดความซับซ้อน — managed service, auto-backup, auto-patching
- ✅ Burstable B1ms tier (~$15-20/เดือน) เพียงพอสำหรับ POC
- ✅ Upgrade เป็น General Purpose ได้เมื่อ scale up
- ⚠️ Shared resource — ถ้า n8n หนักอาจกระทบ Open WebUI performance
- ⚠️ ไม่สามารถ scale database แยกส่วนได้จนกว่าจะแยก instance
