# ADR 0004: Node Pool Strategy — System + Workload + GPU (on-demand)

## Status
Accepted

## Context
AKS cluster ต้องรันหลายประเภท workload:
- AKS system components (CoreDNS, metrics-server, App Routing)
- Application workloads (n8n, Open WebUI)
- GPU workloads (Ollama — optional, เตรียมไว้ภายหลัง)

ใช้ Availability Zones 3 zones ใน Southeast Asia

## Decision
แยก **3 node pools** ด้วยกัน:

| Node Pool | SKU | AZ | Mode |
|---|---|---|---|
| system | Standard_D4s_v5 | 3 nodes (1/AZ) | System |
| workload | Standard_D4s_v5 | 3 nodes (1/AZ) | User |
| gpu | Standard_NC4as_T4_v3 | 0 nodes (scale up later) | User |

## Consequences
- ✅ System pool สถิต — workload scaling ไม่กระทบ system stability
- ✅ Workload pool สามารถ scale up/down ได้อิสระ
- ✅ GPU pool เตรียมไว้เป็น 0 node — ไม่เสียค่าใช้จ่ายจนกว่าจะใช้ Ollama
- ⚠️ POC รวม 6 nodes ทั้งหมด (3+3) — อาจ overkill สำหรับเริ่มต้น แต่จำเป็นสำหรับ AZ
