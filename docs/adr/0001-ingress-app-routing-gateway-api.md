# ADR 0001: Ingress Controller — Application Routing Gateway API (Istio-based)

## Status
Accepted

## Context
AKS deployment สำหรับ n8n + Open WebUI ต้องการ ingress controller สำหรับ:
- Subdomain routing: `n8n.domain.com`, `chat.domain.com`
- TLS termination ด้วย certificates จาก Azure Key Vault

Azure docs (2025-2026) ระบุว่า:
- Application Routing (Managed NGINX) จะ **EOL พฤศจิกายน 2026**
- **Application Routing Gateway API (Istio-based) ได้ GA แล้ว (มิถุนายน 2026)** และเป็น recommended successor

## Decision
ใช้ **Application Routing add-on พร้อม Gateway API implementation (Istio-based)** เป็น ingress controller

## Consequences
- ✅ Future-proof — aligned กับ Azure roadmap, ไม่ต้อง migrate ในอนาคต
- ✅ รองรับ Azure Key Vault integration สำหรับ TLS certificates
- ✅ รองรับ Azure DNS zone management
- ⚠️ ใช้ lightweight Istio control plane แต่ไม่รองรับ sidecar injection หรือ Istio CRDs
- ⚠️ น้อยกว่า NGINX ในเรื่อง community resources และ documentation ณ ตอนนี้
