# ADR 0006: Platform — Azure Container Apps over AKS

## Status
Accepted (supersedes ADR 0001 for ingress, ADR 0004 for node pools)

## Context
เลือก deployment platform สำหรับ n8n + Open WebUI ด้วยเงื่อนไข:
- **Team size:** ทีมเล็ก กำลังคนน้อย ดูแลเองทั้งหมด
- **Budget:** Azure Student $100/เดือน
- **Workload:** POC → Medium scale
- **ต้องเรียน Kubernetes?** ไม่จำเป็นตอนนี้

## Decision
ใช้ **Azure Container Apps (Consumption Plan)** แทน AKS

## Rationale
| Factor | Container Apps | AKS |
|---|---|---|
| Cost (POC) | ~$25-35/เดือน | ~$53-175/เดือน |
| Operational burden | เกือบ 0 — จัดการ container image อย่างเดียว | สูง — K8s upgrades, node patching, networking |
| Scale-to-zero | ✅ 0 = $0 | ❌ ต้องมี node minimum |
| Free managed TLS | ✅ | ❌ |
| GPU support | ✅ Consumption-GPU profile | ✅ GPU node pool |
| Migration path | → AKS ถ้าต้องการ | — |

## Consequences
- ✅ ในงบ $100/เดือน สบาย — actual cost ~$25-35/เดือน
- ✅ คนเดียวดูแลไหว — ไม่ต้องรู้ Kubernetes
- ✅ Scale-to-zero อัตโนมัติตอนไม่มี traffic
- ✅ Free managed TLS certificates (DigiCert)
- ⚠️ Lose Kubernetes learning opportunity
- ⚠️ ถ้าต้อง migrate ขึ้น AKS ภายหลัง ต้องเขียน K8s manifests ใหม่
- ⚠️ ทิ้ง ADR 0001 (Gateway API) และ ADR 0004 (Node Pools) — ไม่ใช้แล้ว
