# ADR 0003: Object Storage — Azure Blob Storage

## Status
Accepted

## Context
ทั้ง n8n และ Open WebUI ต้องการ persistent file storage:
- Open WebUI: uploaded files, documents สำหรับ RAG, generated images
- n8n: binary data storage

ต้องเลือกระหว่าง Azure Blob, Azure Disk (PV), หรือ HostPath

## Decision
ใช้ **Azure Blob Storage** ด้วย S3-compatible API (ใช้ Azure Blob Storage CSI driver หรือ direct S3-compatible endpoint)

## Consequences
- ✅ Managed service — ไม่ต้องจัดการ disk lifecycle
- ✅ ไม่ติดขัดเรื่อง scaling — blob storage ไม่ผูกกับ node
- ✅ ทั้ง n8n และ Open WebUI รองรับ S3-compatible API
- ⚠️ ต้อง configure access key / managed identity ให้ถูกต้อง
