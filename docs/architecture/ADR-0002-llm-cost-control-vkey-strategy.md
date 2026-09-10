# ADR-0002: LLM Cost Control via LiteLLM Virtual Keys (QAS)

- **Status:** Accepted (pending execution)
- **Date:** 2026-09-10
- **Scope:** LLM cost attribution and budget enforcement across HaadThip DIO projects on Genie QAS

## Context

All QAS LLM traffic funnels through one LiteLLM proxy (`app-litellm-qas`) into one Azure AI Foundry resource (`aif-entchat-qas`, 14 deployments, `deploy-*` naming). Original plan: separate per-project deployments on Foundry (prefix names) for isolation. Investigation established:

1. **Attribution already works at LiteLLM layer** — per-key spend tracking is accurate and QAS pricing metadata is complete for all routed models; only `deploy-model-router` lacks pricing.
2. **Budgets are currently absent** — every key on QAS has `max_budget = None` (except one test key). Total historical spend is <$1, so caps can be set generously without breaking anything.
3. **A latent outage exists** — OWUI App Setting `OPENAI_API_KEY` references a Key Vault secret (`litellm-vkey-enterprise-chat-qas`) whose key **no longer exists in the LiteLLM DB (404, orphan)**. The running container still works only because App Service resolves KV references at startup. The next OWUI restart breaks all non-pipe LLM traffic silently.
4. **Procurement trial key ($1,520, `procurement-price-trial-qas`) lives on the Sandbox LiteLLM** (`app-litellm-poc-sand`), which is being decommissioned.

## Decision

Control cost **at the LiteLLM v-key seam only**. Do not fork Foundry deployments per project; Foundry names stay as-is (`deploy-*`).

1. **Canonical bucket:** create one new key `entchat-qas` on QAS LiteLLM with `max_budget = $1,000 USD/month` (`budget_duration = 30d`, hard block on breach) and scope `all-proxy-models` (future model additions need no key edits).
2. **All EnterpriseChat/Genie traffic routes through it** — OWUI global (chat, KB, ingestion embeddings, procurement tool) **and** the procurement Pipe valve. The Procurement trial has **no separate budget bucket**; its usage counts inside the $1,000/month. The $1,520 figure survives only as the DIO umbrella budget intent, not a technical cap.
3. **Project keys where a project exists independently:** `docwise-app-key` is retained as-is (separate spend line for DocWise; budget can be added later). Fondue/IR get keys only when they onboard.
4. **Legacy cleanup on QAS LiteLLM:** delete `incubation`, `incubation-embedding`, `hermes-qas-cache-key-proxy-proof`, `manage-key`, and — after cutover — `enterprise-chat-qas`. Also purge the two orphaned Key Vault secrets (`litellm-vkey-docwise-qas`, `litellm-vkey-enterprise-chat-qas`).
5. **New KV secret `litellm-vkey-entchat-qas`** holds the canonical key; OWUI App Setting repoints to it. One secret per service, matching the existing rule.
6. **Sandbox keys** (`procurement-price-trial-qas` $1,520 and others on `app-litellm-poc-sand`) are retired with the Sandbox; no migration because trial traffic consolidates into `entchat-qas`.

## Consequences

### Positive
- One interface (v-key) carries all cost policy: attribution, cap, scope — Foundry stays a shared pool.
- The orphaned-key outage is fixed proactively instead of discovered at next restart.
- `all-proxy-models` scope removes per-model key maintenance.

### Negative / accepted trade-offs
- TPM/RPM quota remains shared per deployment on Foundry (no noisy-neighbor isolation). Accepted: volume on QAS is trivially low.
- One $1,000/month cap covers everything DIO-QAS; a runaway chat loop can exhaust it and 429 all Genie features including the procurement trial. Mitigation: LiteLLM spend logs + weekly review; cap raises via `PATCH /key/update`.
- Deleting `incubation*` keys assumes no hidden consumer; any straggler will 401 loudly and be diagnosed from spend logs.

## Cutover order (breaks nothing if followed)

1. `POST /key/generate` → `entchat-qas` (1,000 / 30d / all-proxy-models)
2. Store in KV as `litellm-vkey-entchat-qas`
3. OWUI App Setting `OPENAI_API_KEY` → new secret
4. Procurement Pipe valve `LLM_API_KEY` → new key (DB update)
5. Restart OWUI App Service (resolves KV + env fallbacks for tool valves)
6. Verify: Genie chat, KB answer, file ingestion embedding, procurement pipe E2E
7. Delete legacy keys (§4) + orphaned KV secrets
8. Update CONTEXT.md key inventory + Confluence Trial Spec §4 (bucket consolidation)

## Naming convention (for future keys)

`<project>-qas` for monthly buckets (`entchat-qas`), `<app>-app-key` for app-issued keys (`docwise-app-key`), `*-trial-*` reserved for time-boxed pilots with lifetime caps.
