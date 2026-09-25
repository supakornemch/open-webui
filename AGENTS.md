# EnterpriseChat — Agent Guide

Customized **Open WebUI** (image version pinned in `docker/Dockerfile.owui`) + **LiteLLM** proxy + **Azure AI Search** vector backend, deployed to Azure App Service behind a private VNet with Microsoft Teams SSO. Internal name: *Genie* (`genie.haadthip.com`).

**Read [CONTEXT.md](CONTEXT.md) first** — it is the authoritative domain doc (Azure resources, indexes, models, recurring issues, folder guide). This file only covers what an agent needs to *act*; do not duplicate CONTEXT.md here.

## Build & Run

```bash
cp docker/.env.owui.example docker/.env.owui         # fill in secrets first (gitignored)
cp docker/.env.litellm.example docker/.env.litellm   # fill in secrets first (gitignored)
docker compose -f docker/compose.yml up -d --build
```
Local development uses the shared PostgreSQL service at `../local-infra`; `open_webui` and `litellm` remain separate databases.
- Open WebUI → http://localhost:3000 · LiteLLM → http://localhost:4000 · LiteLLM UI → http://localhost:4000/ui
- Start shared infrastructure first: `docker compose -f ../local-infra/compose.yml --env-file ../local-infra/.env up -d`
- Run the repository tests with `.venv/bin/pytest -q`. Search changes additionally use [scripts/test-search-regression.py](scripts/test-search-regression.py); caching changes use [scripts/test-prompt-cache.py](scripts/test-prompt-cache.py). Both need Azure env vars set.

## Architecture (what's custom vs upstream)

The Docker image = **upstream OWUI base + our patches baked in** (see [docker/Dockerfile.owui](docker/Dockerfile.owui)):
- [app/image/patches/client.py](app/image/patches/client.py) — `AzureAISearchClient`, a `VectorDBBase` implementation registered as `VECTOR_DB=azure-ai-search`. `type.py` + `factory.py` patch upstream files to register it.
- [app/image/auth/teams-auth.html](app/image/auth/teams-auth.html) — Teams SSO popup flow (see CONTEXT.md "Teams App" for the flow).
- LiteLLM config + MCP servers → [docker/litellm/config.yaml](docker/litellm/config.yaml).
- Ingestion into `enterprise-docs-idx` → [scripts/ingest/unified.py](scripts/ingest/unified.py) is the main pipeline; per-corpus scripts feed the same index.

## Project-specific rules (easy to get wrong)

- **AMD64 only.** Azure App Service is Linux/AMD64. On ARM Macs, images MUST be built with `docker buildx --platform linux/amd64`. Multi-platform builds produce an OCI index — deploy the AMD64 sub-manifest digest (CONTEXT.md issue #3).
- **VNet blocks all outbound internet.** Anything needing network at runtime (HF model downloads, etc.) must be **baked into the image** at build time — the Dockerfile pre-downloads `sentence-transformers`. SSO/OAuth needs an NSG outbound rule (CONTEXT.md issue #13).
- **Never hardcode secrets.** Config/scripts read from env (`${VAR:?msg}` or `os.environ/VAR`); docs use `<placeholder>` referencing the env files. Real secrets live only in `docker/.env.owui` and `docker/.env.litellm` (both gitignored).
- **One env file per service — never a shared one.** LiteLLM runs `prisma migrate deploy` on whatever `DATABASE_URL` it sees; on a schema it doesn't own it auto-baselines into `DROP TABLE`. A shared `.env` let it wipe the OWUI schema on 2026-07-30. Anything that isn't LiteLLM's own DB must never reach that service.
- **`screenshots/` is a build asset**, not junk — [docker/Dockerfile.owui](docker/Dockerfile.owui) copies it into the image and the served manual links into it. It is deliberately un-gitignored. Don't delete it.
- **Served manual source of truth** is [app/image/static/genie-setup-manual.html](app/image/static/genie-setup-manual.html) (copied into the image). Do not resurrect a top-level `docs/` copy.
- **OWUI internals are async** (v0.10.2+). For bulk DB work use `SessionLocal()` + raw SQL, not `get_db()` + ORM (CONTEXT.md issue #12).

## Verification

Use the repository virtual environment, not the system Python:

```bash
.venv/bin/python -m compileall app scripts tests features
.venv/bin/pytest -q
```

Targeted checks:

- Fabric changes: `.venv/bin/pytest -q tests/test_fabric_*.py tests/test_deploy_fabric_delegated_tool.py`
- Procurement changes: `.venv/bin/pytest -q tests/unit/procurement`
- Search changes: `scripts/test-search-regression.py` with the required Azure variables
- Docker changes: `docker buildx build --platform linux/amd64 -f docker/Dockerfile.owui .`
- Workflow changes: `actionlint .github/workflows/deploy.yml`

Do not claim an external deployment succeeded without reading back the deployed image digest and readiness endpoint.


Branch flow: `feature/*` → `release/mvp` → `qas` → `main`. Branch from latest `release/mvp`; use conventional-commit prefixes (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`). Full model in [CONTEXT.md](CONTEXT.md) "Git Strategy". Only commit when asked; never commit `docker/.env*` (only the `.example` files).
