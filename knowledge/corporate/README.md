# Haadthip Public Documents

Document corpus for the DocWise **Pipeline** — sourced from Haad Thip Public Company Limited (HTC). Includes both internal operational guides and public regulatory disclosures for ingestion into **Content Understanding** → LLM **Summary** → **Data Hook**.

## Directory Structure

```
haadthip-corporate/
├── 01-security/          MFA, VPN, session management        (5 docs)
├── 02-email/             Exchange / O365 setup & management   (7 docs)
├── 03-meeting-room/      Board meeting room booking & usage   (2 docs)
├── 04-it-policy/         DLP endpoint policy                  (1 doc)
└── 05-public-disclosure/ SET/SEC regulatory filings           (3 docs)
```

**Total: 18 Documents across 5 categories**

## Overview

| # | Category | Docs | Visibility | Primary Language | Pipeline Priority |
|---|----------|------|------------|------------------|-------------------|
| 01 | Security | 5 | 🔒 Internal | EN + TH | Medium — step extraction |
| 02 | Email | 7 | 🔒 Internal | TH (5) + EN (2) | Low — IT self-service FAQ |
| 03 | Meeting Room | 2 | 🔒 Internal | EN + TH | Low — quick PoC test set |
| 04 | IT Policy | 1 | 🔒 Internal | EN | Medium — rule extraction |
| 05 | Public Disclosure | 3 | ✅ Public | EN | **High** — main PoC corpus |

## ⚠️ Visibility Note

- **Categories 01–04** are **internal Documents** (IT manuals, policies). Do NOT expose externally without authorization.
- **Category 05** is **public regulatory disclosure** — safe for external-facing PoC.

## Quick Start for PoC

For the **chat from AI search** PoC, start with:

1. `05-public-disclosure/htc-one-report-2024-en.pdf` — broadest Q&A surface
2. `05-public-disclosure/htc-sustainability-report-2024-en.pdf` — ESG + charts
3. `05-public-disclosure/htc-agm2024-minutes-en.pdf` — structured resolution data

See each category's `README.md` for detailed Pipeline notes.
