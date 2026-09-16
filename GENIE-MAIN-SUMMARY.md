# Genie Main v1.0.0 — Production Promotion Summary

**Created**: 2026-09-16  
**Status**: Ready for deployment  
**Branch**: `release/mvp-1.0.0`

---

## What Was Done

### 1. **Root Cause Analysis**
Analyzed chat export from POC model (`genieai-poc-rbac`) — found that:
- Model never called `fabric_query_delegated_user_qas` tool despite Fabric questions
- Model only called `list_knowledge` (wrong tool for data queries)
- System prompt mentioned Fabric but didn't enforce tool usage
- Native Tool models don't work well with REST API (require manual tool loop)

### 2. **Solution: Pipe-Based Model**
Created two new Pipe functions:

#### A. `app/functions/fabric_delegated_pipe.py`
- Experimental Fabric-only Pipe
- Tool loop inside Pipe (no UI dependency)
- Delegated token support via `__oauth_token__` + `__user__`

#### B. `app/functions/genie_main_pipe.py` ⭐
- **Production Genie AI model**
- Combines system prompt from POC + Fabric tool
- REST API one-call support (no multi-turn loop)
- Explicit discovery query instruction
- Max 8 tool rounds (vs 6 in POC)

### 3. **System Prompt Enhancement**
Added explicit Fabric query rules:
```markdown
เมื่อผู้ใช้ถามว่า "เข้าถึงข้อมูลอะไรได้จาก Fabric":
เรียก query_fabric ทันทีด้วย SQL:
SELECT TOP 10 table_schema, table_name 
FROM INFORMATION_SCHEMA.TABLES 
WHERE table_schema NOT IN ('sys', 'INFORMATION_SCHEMA')
```

### 4. **Documentation**
- `docs/genie-main-promotion-plan.md` — full deployment guide
- Testing checklist (UI + REST API)
- Rollback plan
- Migration announcement template

### 5. **Deployment Script**
- `scripts/deploy-genie-main.sh` — automated deployment
- Builds AMD64 image (Azure App Service requirement)
- Pushes to ACR
- Updates App Service
- Health check
- Rollback instructions

---

## Files Created/Modified

### New Files
```
app/functions/fabric_delegated_pipe.py   (experimental)
app/functions/genie_main_pipe.py        (production ⭐)
docs/genie-main-promotion-plan.md
scripts/deploy-genie-main.sh
```

### Modified Files (uncommitted from previous work)
```
app/tools/fabric-query-delegated.py
app/tools/fabric-skill.md
app/tools/procurement-search.py
requirements/procurement-price-chat/...
tests/test_fabric_*.py
```

---

## Deployment Steps (Manual)

### Option A: Automated (Recommended)
```bash
cd /Users/supakorn.emch/Workspace/Haadthip/EnterpriseChat
./scripts/deploy-genie-main.sh
```

### Option B: Manual
1. **Build & Push**
   ```bash
   cd docker
   docker buildx build --platform linux/amd64 \
     -f Dockerfile.owui \
     -t acrentchatqas.azurecr.io/entchat-owui:genie-v1.0.0 .
   docker push acrentchatqas.azurecr.io/entchat-owui:genie-v1.0.0
   ```

2. **Deploy**
   ```bash
   az webapp config container set \
     --resource-group RG-INCUBATION-AI-QAS-SEA \
     --name app-entchat-owui-qas \
     --docker-custom-image-name acrentchatqas.azurecr.io/entchat-owui:genie-v1.0.0
   ```

3. **Configure in UI**
   - Go to https://genie-qas.haadthip.com/workspace/functions
   - Configure `genie_main_pipe` valves
   - Go to Workspace → Models → Create
   - Model ID: `genieai`
   - Base Model: `genie_main_pipe`
   - System Prompt: paste from `docs/genie-main-promotion-plan.md`
   - Knowledge: attach `ข้อมูลทั่วไป`
   - Capabilities: citations, status_updates, usage, memory enabled
   - Custom params: `prompt_cache_key: genie-qas`

4. **Test**
   ```bash
   # UI: Create chat, select "genieai", ask:
   "ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้จาก Fabric"
   
   # REST API:
   curl -X POST https://genie-qas.haadthip.com/api/chat/completions \
     -H "Authorization: Bearer $OWUI_QAS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "genieai",
       "messages": [
         {"role": "user", "content": "ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้"}
       ]
     }'
   ```

---

## Key Improvements Over POC

| Feature | `genieai-poc-rbac` (POC) | `genieai` (Production) |
|---------|--------------------------|------------------------|
| **Architecture** | Native Tool model | Pipe model |
| **REST API one-call** | ❌ (multi-turn manual) | ✅ |
| **Tool call enforcement** | ⚠️ Weak (model chooses) | ✅ Strong (explicit instruction) |
| **Discovery query** | ❌ Not mentioned | ✅ Built into prompt |
| **Tool loop** | Open WebUI server | Inside Pipe (self-contained) |
| **Max rounds** | 6 | 8 |
| **Delegated token** | ✅ | ✅ |
| **Permission preflight** | ✅ | ✅ |
| **Prompt cache** | ✅ `genie-qas` | ✅ `genie-qas` |

---

## Testing Checklist

Before marking as complete:

- [ ] Image builds successfully for `linux/amd64`
- [ ] Image pushed to `acrentchatqas.azurecr.io`
- [ ] App Service deploys without errors
- [ ] Health check returns HTTP 200
- [ ] Function `genie_main_pipe` appears in UI
- [ ] Valves configured correctly
- [ ] Model `genieai` created with correct system prompt
- [ ] UI test: Discovery query returns table list
- [ ] UI test: Quantitative question calls Fabric
- [ ] UI test: General question doesn't call Fabric
- [ ] REST API test: One-call completion works
- [ ] Citations display correctly
- [ ] Status updates show tool calls

---

## Rollback Plan

If deployment fails or issues occur:

1. **Immediate rollback** (preserve current image tag first):
   ```bash
   # Get current image
   az webapp config container show \
     --resource-group RG-INCUBATION-AI-QAS-SEA \
     --name app-entchat-owui-qas
   
   # Rollback to previous
   az webapp config container set \
     --resource-group RG-INCUBATION-AI-QAS-SEA \
     --name app-entchat-owui-qas \
     --docker-custom-image-name <previous-image>
   ```

2. **Model-level rollback** (no redeploy needed):
   - Change default model back to `genieai-poc-rbac`
   - Users can manually select POC model in UI

3. **Hide new model**:
   - Archive `genieai` model in UI
   - Keep `genieai-poc-rbac` as default

---

## Next Steps

1. ✅ Code ready — review this summary
2. ⏳ **Deploy** — run `./scripts/deploy-genie-main.sh`
3. ⏳ **Configure** — set up model in UI
4. ⏳ **Test** — verify UI + REST API
5. ⏳ **Announce** — send migration notice to users
6. ⏳ **Monitor** — track success metrics for 2 weeks
7. ⏳ **Archive POC** — deprecate `genieai-poc-rbac` after stable period

---

## Questions for Review

1. **Image tag**: Use `genie-v1.0.0` or different naming convention?
2. **Default model**: Set `genieai` as default immediately or gradual rollout?
3. **POC model**: Keep active or archive immediately?
4. **Announcement**: Send now or after testing period?
5. **Monitoring**: Any specific metrics to track beyond success checklist?

---

**Ready to deploy?** ตรวจสอบแผนข้างบนแล้วบอกได้เลยครับ หรือถ้ามีข้อสงสัย/ต้องการแก้ไขอะไร บอกได้ก่อน deploy
