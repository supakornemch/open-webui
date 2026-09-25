# ADR-0001: One Procurement Domain Module Behind Tool and Pipe Adapters

- **Status:** Proposed
- **Date:** 2026-09-10
- **Scope:** Procurement Price Assistant on Genie QAS

## Context

The Open WebUI Tool in `app/openwebui/tools/procurement-search.py` and the Pipe in `app/openwebui/functions/procurement_price_pipe.py` both implement procurement behavior. The overlap includes Azure AI Search client setup, embedding calls, OData filter construction, category and quantity fallback, tier selection, total-price calculation and result shaping.

The Tool and Pipe are separate runtime adapters, but their business behavior is not separated from those adapters. Their interfaces are therefore wide and their implementations are drifting. The QAS trial depends on price correctness and MOQ handling, so a one-path fix that does not reach the other path is a material risk.

## Decision

Create one internal Procurement domain module that owns:

- product retrieval request construction
- Search result normalization
- category and quantity fallback policy
- tier validation and selection
- below-MOQ and no-matching-tier outcomes
- deterministic total-price calculation
- stable result facts for the LLM

Keep the Open WebUI Tool and Pipe as thin adapters at the external seam. They translate runtime arguments/events into the domain interface and translate domain results into the Tool/Pipe response shape.

The first implementation may remain in-process. A separate external interface or network service is not justified by the current codebase.

## Consequences

### Positive

- One interface becomes the test surface for pricing correctness.
- Fixes have locality: one implementation changes both runtime paths.
- The Tool and Pipe gain leverage from shared tier and fallback behavior.
- Azure SDK details remain behind an internal adapter seam.
- Tests can use an in-memory Search adapter without network calls.

### Negative

- Existing duplicated logic must be reconciled before deletion.
- The first refactor touches both runtime adapters and their deployment files.
- Response compatibility must be preserved for existing model prompts.

## Rejected alternatives

### Keep duplicate implementations

Rejected because the behavior is already drifting and pricing errors are user-visible.

### Make the Tool call the Pipe

Rejected because it couples two Open WebUI runtime mechanisms and leaves the domain behavior shallow rather than creating a stable seam.

### Extract a standalone microservice

Rejected for now. It adds deployment, authentication and network failure modes without a second independent consumer that requires a process seam.

## Migration outline

1. Add an internal package with explicit domain types for `SearchRequest`, `Product`, `Tier`, `SearchOutcome` and `CalculationOutcome`.
2. Add a Search adapter interface and an Azure AI Search implementation.
3. Move calculator tests to the domain interface; add fallback and result-normalization tests.
4. Convert the Pipe to an adapter and run the existing Pipe tool-loop regression.
5. Convert the Open WebUI Tool to an adapter and preserve event/status output.
6. Delete duplicated tier and fallback implementations after parity tests pass.
7. Update the system architecture document and deployment runbook.
