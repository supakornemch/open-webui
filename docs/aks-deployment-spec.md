# AKS Deployment Spec — Open WebUI + AI Search (Reference)

> **Status:** Reference Doc | **Last Updated:** 2026-07-03
> **Note:** ทีมเลือก Container Apps เป็นหลัก — AKS spec นี้เป็น reference สำหรับ future migration

Deploy **Open WebUI** (AI chat interface) + **Azure AI Search** (RAG + Agentic Retrieval) บน Azure Kubernetes Service (AKS)

---

## 1. Executive Summary

Deploy **Open WebUI** (AI chat interface) + **Azure AI Search** (RAG + Agentic Retrieval) บน Azure Kubernetes Service (AKS) — เริ่มจาก POC minimal แล้ว scale ขึ้นเป็น Medium workload ได้

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure VNet (10.0.0.0/16)                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AKS Cluster (Azure CNI Overlay)          │  │
│  │                   Pod CIDR: 10.244.0.0/16             │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │System Pool  │  │ Workload    │  │ GPU Pool    │   │  │
│  │  │D4s_v5 × 3  │  │ Pool        │  │ NC4as_T4    │   │  │
│  │  │(1 per AZ)  │  │ D4s_v5 × 3  │  │ × 0 (later) │   │  │
│  │  │             │  │ (1 per AZ)  │  │             │   │  │
│  │  │ CoreDNS     │  │             │  │             │   │  │
│  │  │ metrics     │  │  Open WebUI │  │  Ollama     │   │  │
│  │  │ App Routing │  │  Open WebUI │  │ (future)    │   │  │
│  │  │             │  │  Prometheus │  │             │   │  │
│  │  │             │  │  Grafana    │  │             │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐   │
│  │ Azure    │  │ PostgreSQL│  │ Azure    │  │ Azure   │   │
│  │ OpenAI   │  │ Flex Srv  │  │ Blob     │  │ Key     │   │
│  │ Service  │  │ B1ms→ GP  │  │ Storage  │  │ Vault   │   │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Internet ──► Gateway API (Istio) ──► TLS terminate  │  │
│  │              chat.domain.com         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Cluster Specification

### 3.1 Cluster Config

| Parameter | Value | Notes |
|---|---|---|
| **Region** | `southeastasia` | Azure Southeast Asia (Singapore) |
| **Kubernetes Version** | `1.33` (latest GA) | — |
| **Network Plugin** | `azure` + `overlay` | Azure CNI Overlay |
| **Pod CIDR** | `10.244.0.0/16` | Default overlay CIDR |
| **Service CIDR** | `10.0.0.0/16` (auto) | Managed by AKS |
| **DNS Service IP** | auto-configured | — |
| **Load Balancer SKU** | `standard` | Required for AZ + App Routing |
| **Identity** | SystemAssigned | Managed identity |
| **SLA/Uptime** | Free tier (POC) → Paid Standard when production |

### 3.2 Node Pools

#### System Pool

| Parameter | Value |
|---|---|
| **Name** | `system` |
| **SKU** | `Standard_D4s_v5` |
| **vCPUs** | 4 |
| **Memory** | 16 GiB |
| **Node Count** | 3 (1 per AZ) |
| **Autoscale** | Off (fixed for system) |
| **Max Pods/Node** | 30 |
| **Taints** | `CriticalAddonsOnly=true:NoSchedule` |
| **Roles** | CoreDNS, metrics-server, app-routing, gateway API pods |

#### Workload Pool

| Parameter | Value |
|---|---|
| **Name** | `workload` |
| **SKU** | `Standard_D4s_v5` |
| **vCPUs** | 4 |
| **Memory** | 16 GiB |
| **Node Count** | 3 (1 per AZ) |
| **Autoscale** | 2–6 nodes |
| **Max Pods/Node** | 110 |
| **Roles** | Open WebUI, Prometheus, Grafana |

#### GPU Pool (Future / On-Demand)

| Parameter | Value |
|---|---|
| **Name** | `gpu` |
| **SKU** | `Standard_NC4as_T4_v3` |
| **vCPUs** | 4 |
| **Memory** | 28 GiB |
| **GPU** | 1× NVIDIA T4 (16 GB VRAM) |
| **Node Count** | 0 (scaled to zero) |
| **Autoscale** | 0–3 nodes |
| **Roles** | Ollama + local LLM inference |

> **Note:** GPU pool ตั้งเป็น 0 node — ไม่เสียค่าใช้จ่ายจนกว่าจะ scale up เพื่อรัน Ollama

---

## 4. Application Resource Allocation

### 4.1 Open WebUI

| Resource | Request | Limit |
|---|---|---|
| **CPU** | 250m (~0.25 vCPU) | 1000m (1 vCPU) |
| **Memory** | 512 MiB | 2048 MiB (2 GiB) |
| **Replicas** | 2 | — |
| **Storage** | Azure Blob (for RAG docs, uploads) | — |

### 4.3 Prometheus + Grafana

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit |
|---|---|---|---|---|
| **Prometheus** | 200m | 512 MiB | 500m | 1024 MiB |
| **Grafana** | 100m | 256 MiB | 200m | 512 MiB |
| **kube-prometheus-stack** (optional) | 300m | 512 MiB | 800m | 1024 MiB |

---

## 5. Ingress / Networking

### 5.1 Ingress Controller

| Parameter | Value |
|---|---|
| **Type** | Application Routing + Gateway API (Istio-based) |
| **GatewayClass** | `approuting-istio` |
| **DNS Integration** | Azure DNS Zone |
| **TLS** | Azure Key Vault certificates |
| **AZ Enable CLI** | `az aks create --enable-app-routing --enable-app-routing-istio` |

### 5.2 Routing Table

| Hostname | Service | Port | TLS |
|---|---|---|---|
| **chat.yourdomain.com** | Open WebUI (namespace: `open-webui`) | 8080 | ✅ |

### 5.3 Gateway API Resources (Conceptual)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: enterprisechat-gateway
spec:
  gatewayClassName: approuting-istio
  listeners:
  - name: https
    port: 443
    protocol: HTTPS
    tls:
      certificateRefs:
      - name: open-webui-tls-cert    # auto-managed by App Routing + Key Vault
    allowedRoutes:
      namespaces:
        from: All
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: open-webui-route
  namespace: open-webui
spec:
  parentRefs:
  - name: enterprisechat-gateway
  hostnames: ["chat.yourdomain.com"]
  rules:
  - backendRefs:
    - name: open-webui
      port: 8080
```

---

## 6. Database — Azure PostgreSQL Flexible Server

### 6.1 Instance Config

| Parameter | POC (Initial) | Medium (Scale Up) |
|---|---|---|
| **Tier** | Burstable | General Purpose |
| **SKU** | B1ms | Standard_D2s_v3 |
| **vCores** | 1 | 2 |
| **Memory** | 2 GiB | 8 GiB |
| **Storage** | 32 GB (grow auto) | 128 GB |
| **Backup** | 7 days (default) | 14 days |
| **HA** | None | Zone-redundant |
| **Network** | Public (POC) | Private Endpoint |
| **SSL** | Required | Required |

### 6.2 Databases & Users

| Database | Owner | Service |
|---|---|---|
| `openwebui` | `openwebui_user` | Open WebUI |

### 6.3 Default `values.yaml` Snippets

**Open WebUI Helm chart:**
```yaml
database:
  type: postgres
  postgres:
    host: enterprisechat-pg.postgres.database.azure.com
    port: 5432
    username: openwebui_user
    database: openwebui
DATABASE_URL: "postgresql://openwebui_user:<password>@enterprisechat-pg.postgres.database.azure.com:5432/openwebui"
```

---

## 7. Storage — Azure Blob

| Parameter | Value |
|---|---|
| **Account Kind** | StorageV2 (general purpose v2) |
| **Replication** | LRS (POC) → GRS (medium) |
| **Tier** | Hot |
| **Containers** | `openwebui-uploads` |
| **Network** | Public (POC) → Private Endpoint |

---

## 8. Namespace Layout

| Namespace | Contents |
|---|---|
| `open-webui` | Open WebUI deployment, service, secrets, configmaps |
| `monitoring` | Prometheus, Grafana, ServiceMonitors, PodMonitors |
| `app-routing-system` | AKS App Routing Gateway API operator (auto-created) |
| `kube-system` | AKS system components (auto-created) |

---

## 9. Deployment Steps (Execution Order)

### Phase 1 — Infrastructure

```bash
# 1. Create resource group
az group create --name rg-enterprisechat-poc --location southeastasia

# 2. Create AKS cluster with all add-ons
az aks create \
  --resource-group rg-enterprisechat-poc \
  --name aks-enterprisechat \
  --location southeastasia \
  --kubernetes-version 1.33 \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --pod-cidr 10.244.0.0/16 \
  --enable-app-routing \
  --enable-app-routing-istio \
  --node-count 3 \
  --node-vm-size Standard_D4s_v5 \
  --zones 1 2 3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 3 \
  --generate-ssh-keys

# 3. Add workload node pool
az aks nodepool add \
  --resource-group rg-enterprisechat-poc \
  --cluster-name aks-enterprisechat \
  --name workload \
  --node-vm-size Standard_D4s_v5 \
  --node-count 3 \
  --zones 1 2 3 \
  --mode User \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 6

# 4. Add GPU node pool (scaled to zero)
az aks nodepool add \
  --resource-group rg-enterprisechat-poc \
  --cluster-name aks-enterprisechat \
  --name gpu \
  --node-vm-size Standard_NC4as_T4_v3 \
  --node-count 0 \
  --zones 1 2 3 \
  --mode User \
  --enable-cluster-autoscaler \
  --min-count 0 \
  --max-count 3

# 5. Get credentials
az aks get-credentials --resource-group rg-enterprisechat-poc --name aks-enterprisechat
```

### Phase 2 — Supporting Services

```bash
# 6. Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group rg-enterprisechat-poc \
  --name enterprisechat-pg \
  --location southeastasia \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 16 \
  --admin-user pgadmin \
  --database-name postgres

# 7. Create application database
az postgres flexible-server db create \
  --resource-group rg-enterprisechat-poc \
  --server-name enterprisechat-pg \
  --database-name openwebui

# 8. Create Storage Account
az storage account create \
  --resource-group rg-enterprisechat-poc \
  --name enterprisechatstg \
  --location southeastasia \
  --sku Standard_LRS \
  --kind StorageV2

# 9. Get storage key & create containers
STORAGE_KEY=$(az storage account keys list \
  --resource-group rg-enterprisechat-poc \
  --account-name enterprisechatstg \
  --query [0].value -o tsv)

az storage container create --name openwebui-uploads --account-name enterprisechatstg

# 10. Create Key Vault
az keyvault create \
  --resource-group rg-enterprisechat-poc \
  --name enterprisechat-kv \
  --location southeastasia

# 11. Attach Key Vault to App Routing
KEYVAULT_ID=$(az keyvault show --name enterprisechat-kv --query id -o tsv)
az aks approuting update \
  --resource-group rg-enterprisechat-poc \
  --name aks-enterprisechat \
  --enable-kv \
  --attach-kv $KEYVAULT_ID
```

### Phase 3 — Applications

```bash
# 11. Create namespace
kubectl create namespace open-webui
kubectl create namespace monitoring

# 12. Install Open WebUI via Helm
helm repo add open-webui https://helm.openwebui.com/
helm upgrade --install open-webui open-webui/open-webui \
  --namespace open-webui \
  --values open-webui-values.yaml

# 13. Install Prometheus + Grafana via Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring-values.yaml
```

---

## 10. Helm Values (Key Configurations)

### Open WebUI `open-webui-values.yaml`

```yaml
replicaCount: 2

image:
  tag: main

resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 2048Mi

database:
  type: postgres

ingress:
  enabled: false  # Using Gateway API

extraEnvVars:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: open-webui-db-secret
        key: url
  - name: OPENAI_API_BASE
    value: "https://<your-azure-openai>.openai.azure.com/"
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: open-webui-ai-secret
        key: api-key
  - name: STORAGE_PROVIDER
    value: "s3"
  - name: S3_ENDPOINT_URL
    value: "https://enterprisechatstg.blob.core.windows.net"
  - name: S3_BUCKET_NAME
    value: "openwebui-uploads"

service:
  type: ClusterIP
  port: 8080
```

### Monitoring `monitoring-values.yaml`

```yaml
prometheus:
  prometheusSpec:
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 1024Mi
    retention: 7d
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 20Gi

grafana:
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 200m
      memory: 512Mi
  adminPassword: changeme  # Use secret for production
  ingress:
    enabled: true
    hosts:
      - monitor.yourdomain.com
```

---

## 11. Estimated Monthly Cost Breakdown (POC)

| Resource | SKU | Qty | Monthly (Approx.) |
|---|---|---|---|
| AKS Control Plane | Free tier | 1 | $0 |
| System Pool (D4s_v5) | Pay-as-you-go | 3 × $175 | $525 |
| Workload Pool (D4s_v5) | Pay-as-you-go | 3 × $175 | $525 |
| PostgreSQL Flex (B1ms) | Burstable | 1 | ~$15 |
| AI Search Basic | 1 SU | 1 | ~$73 |
| Blob Storage | LRS Hot | ~5 GB | <$1 |
| Key Vault | — | 1 | <$5 |
| Azure OpenAI | Varies by usage | — | ~$20–50 (POC) |
| **Total (POC)** | | | **~$1,163/month** |

> ⚠️ **Warning:** ผมรวม 2 node pools (system + workload) = 6 nodes ซึ่งอาจมากเกินไปสำหรับ POC Budget ถ้าจำเป็นต้องลด ดู Section 12

---

## 12. Cost-Optimized Minimal Variant

สำหรับ Azure Student หรือ POC แบบประหยัดงบ (~$100/month):

| Change | Result |
|---|---|
| **รวม system + workload เป็น pool เดียว** | 3 nodes แทน 6 |
| **ไม่มี System Pool taints** | All workloads รันรวมกัน |
| **PostgreSQL B1ms** | ~$15/month |
| **3× D4s_v5** | 3 × $175 = $525 |
| **Total (Minimal)** | **~$565/month** |

ยังเกิน $100 มาก... ตัวเลือกเพิ่มเติม:

| Optimization | Impact |
|---|---|
| **Use B2s_v3 (2 vCPU, 4GB)** | 3 × ~$45 = $135 (system only, workload light) |
| **Use B2pls_v2 (2 vCPU, 4GB)** | cheapest burstable ~$35-40/month |
| **Single node (no AZ)** | dev-only, ไม่ production ready |
| **Turn off VMs when not in use** | Stop deallocate outside work hours — save 60-70% |

> **Azure Student $100 credit** ไม่เพียงพอสำหรับ AKS node แบบ 24/7 — แต่ถ้ารันเฉพาะช่วงทำงานและใช้ Spot/Stopped instances ก็พอไหวครับ

---

## 13. Scaling Path: POC → Medium

| Component | POC | Medium |
|---|---|---|
| **System Pool** | D4s_v5 × 3 | D4s_v5 × 3 (unchanged) |
| **Workload Pool** | D4s_v5 × 3 | D8s_v5 × 4–6 (auto-scale) |
| **GPU Pool** | 0 nodes | NC4as_T4_v3 × 1–3 |
| **PostgreSQL** | B1ms (Burstable) | Standard_D2s_v3 (General Purpose) |
| **Blob Storage** | LRS → GRS | GRS + Private Endpoint |
| **Monitoring** | Prometheus 7d retention | Prometheus 30d + Azure Monitor |
| **Ingress** | Gateway API (Istio) | Same + Private Endpoint support |
| **Network** | Public all | Private Endpoints for DB, Storage, OpenAI |

---

## 14. Manifest Tree (Final File Layout)

```
/
├── CONTEXT.md                                # Domain glossary
├── docs/
│   ├── adr/
│   │   ├── 0001-ingress-app-routing-gateway-api.md
│   │   ├── 0002-shared-postgresql-flexible-server.md
│   │   ├── 0003-azure-blob-object-storage.md
│   │   ├── 0004-node-pool-strategy.md
│   │   └── 0005-llm-backend-hybrid.md
│   └── aks-deployment-spec.md                # THIS DOCUMENT
├── helm/
│   ├── open-webui-values.yaml
│   └── monitoring-values.yaml
├── k8s/
│   ├── namespaces.yaml
│   ├── gateway.yaml
│   ├── open-webui-route.yaml
│   └── secrets/
│       ├── open-webui-db-secret.yaml
│       └── open-webui-ai-secret.yaml
└── scripts/
    ├── 01-create-infra.sh
    ├── 02-deploy-apps.sh
    └── 03-cleanup.sh
```

---

## 15. Key ADRs (Quick Reference)

| ADR | Decision | Status |
|---|---|---|
| [0001](adr/0001-ingress-app-routing-gateway-api.md) | Gateway API (Istio) over NGINX | Accepted |
| [0002](adr/0002-shared-postgresql-flexible-server.md) | Shared PostgreSQL Flexible Server | Accepted |
| [0003](adr/0003-azure-blob-object-storage.md) | Azure Blob for object storage | Accepted |
| [0004](adr/0004-node-pool-strategy.md) | 3 node pools (sys/wkld/gpu) | Accepted |
| [0005](adr/0005-llm-backend-hybrid.md) | Hybrid LLM: Azure OpenAI + Ollama | Accepted |
