#!/bin/bash
# =====================================================
# Download Haadthip IR Documents for AI Search Ingestion
# =====================================================
# Source: https://www.haadthip.com/en/investor-relations/document/annual-reports
# 
# Usage: bash download-ir-docs.sh
# =====================================================

set -e

BASE_DIR="/Users/supakorn.emch/Workspace/Haadthip/EnterpriseChat/documents/haadthip-ir"
ANNUAL_DIR="$BASE_DIR/01-annual-reports"
FINANCIAL_DIR="$BASE_DIR/02-financial-data"
DISCLOSURE_DIR="$BASE_DIR/03-company-disclosures"

mkdir -p "$ANNUAL_DIR" "$FINANCIAL_DIR" "$DISCLOSURE_DIR"

echo "=========================================="
echo "📥 Downloading Haadthip IR Documents"
echo "=========================================="

# ==========================================
# 1. Annual Reports / One Report (2025-2012)
# ==========================================
echo ""
echo "━━━ 1. Annual Reports / One Report ━━━"

# 2025 - Latest
echo "→ 2025: htc-one-report2025-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-one-report2025-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2025/htc-one-report2025-en.pdf" &
curl -sL -o "$ANNUAL_DIR/htc-e-one-report2025-en.pdf" \
  "https://www.haadthip.com/storage/document/annual-reports/2025/htc-e-one-report2025-en.pdf" &

# 2024 - Skip if already exists in haadthip-public
if [ ! -f "$BASE_DIR/../haadthip-public/05-public-disclosure/htc-one-report-2024-en.pdf" ]; then
  echo "→ 2024: htc-one-report2024-en.pdf"
  curl -sL -o "$ANNUAL_DIR/htc-one-report2024-en.pdf" \
    "https://hub.optiwise.io/storage/21/annual-report/2024/htc-one-report2024-en.pdf" &
fi
echo "→ 2024: htc-e-one-report2024-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-e-one-report2024-en.pdf" \
  "https://www.haadthip.com/storage/document/annual-reports/2024/htc-e-one-report2024-en.pdf" &

# 2023
echo "→ 2023: htc-one-report2023-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-one-report2023-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2023/htc-one-report2023-en.pdf" &

# 2022
echo "→ 2022: htc-one-report2022-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-one-report2022-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2022/htc-one-report2022-en.pdf" &

# 2021
echo "→ 2021: htc-one-report2021-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-one-report2021-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2021/20220714-htc-one-report2021-en.pdf" &

# Wait for first batch
wait
echo "✅ Batch 1 (2025-2021) complete"

# 2020 Annual Report + Form 56-1
echo "→ 2020: htc-ar2020-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2020-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2020/20210423-htc-ar2020-en.pdf" &
echo "→ 2020: htc-form561-2020-th.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2020-th.pdf" \
  "https://hub.optiwise.io/en/documents/19610/20210405-htc-form561-2020-th.pdf" &

# 2019
echo "→ 2019: htc-ar2019-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2019-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2019/20200713-htc-ar2019-en.pdf" &
echo "→ 2019: htc-form561-2019-th.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2019-th.pdf" \
  "https://hub.optiwise.io/en/documents/10410/20200505-htc-form561-2019-th.pdf" &

# 2018
echo "→ 2018: htc-ar2018-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2018-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2018/20190411-htc-ar2018-en.pdf" &
echo "→ 2018: htc-form561-2018-th.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2018-th.pdf" \
  "https://hub.optiwise.io/en/documents/10411/20190412-htc-form561-2018-02.pdf" &

# 2017
echo "→ 2017: htc-ar2017.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2017.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2017/20180410-htc-ar2017.pdf" &
echo "→ 2017: htc-form561-2017.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2017.pdf" \
  "https://hub.optiwise.io/en/documents/10412/20180410-htc-form561-2017.pdf" &

# Wait for second batch
wait
echo "✅ Batch 2 (2020-2017) complete"

# 2016
echo "→ 2016: htc-ar2016-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2016-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2016/htc-ar2016-en.pdf" &
echo "→ 2016: htc-form561-2016.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2016.pdf" \
  "https://hub.optiwise.io/en/documents/10413/htc-form561-2016.pdf" &

# 2015
echo "→ 2015: htc-ar2015-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2015-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2015/htc-ar2015-en.pdf" &
echo "→ 2015: htc-form561-2015.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2015.pdf" \
  "https://hub.optiwise.io/en/documents/10414/htc-form561-2015.pdf" &

# 2014
echo "→ 2014: htc-ar2014-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2014-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2014/htc-ar2014-en.pdf" &
echo "→ 2014: htc-form561-2014.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2014.pdf" \
  "https://hub.optiwise.io/en/documents/10415/htc-form561-2014.pdf" &

# 2013
echo "→ 2013: htc-ar2013-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2013-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2013/htc-ar2013-en.pdf" &
echo "→ 2013: htc-form561-2013.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2013.pdf" \
  "https://hub.optiwise.io/en/documents/10416/htc-form561-2013.pdf" &

# 2012
echo "→ 2012: htc-ar2012-en.pdf"
curl -sL -o "$ANNUAL_DIR/htc-ar2012-en.pdf" \
  "https://hub.optiwise.io/storage/21/annual-report/2012/htc-ar2012-en.pdf" &
echo "→ 2012: htc-form561-2012.pdf"
curl -sL -o "$ANNUAL_DIR/htc-form561-2012.pdf" \
  "https://hub.optiwise.io/en/documents/10417/htc-form561-2012.pdf" &

# Wait for third batch
wait
echo "✅ Batch 3 (2016-2012) complete"

# ==========================================
# 2. Financial Data
# ==========================================
echo ""
echo "━━━ 2. Financial Data ━━━"

echo "→ Earning Results Q1/2026"
curl -sL -o "$FINANCIAL_DIR/htc-earning-results-q1-2026.pdf" \
  "https://hub.optiwise.io/en/documents/220512/20260520-1q2026-results.pdf" &

echo "→ Fact Sheet 3M/2026"
curl -sL -o "$FINANCIAL_DIR/htc-factsheet-3m2026.pdf" \
  "https://hub.optiwise.io/storage/21/fact-sheet/2026/htc-factsheet-3m2026.pdf" &

wait
echo "✅ Financial Data complete"

# ==========================================
# 3. Company Disclosures (latest)
# ==========================================
echo ""
echo "━━━ 3. Company Disclosures ━━━"

echo "→ MD&A Q1/2026"
curl -sL -o "$DISCLOSURE_DIR/htc-mda-q1-2026.pdf" \
  "https://hub.optiwise.io/en/documents/218967/644370581ADEC43C2A43725E1ADAC538670F775A12D9B0391246715F1FDAC24B6447762868D3B03D643275586BDECC4E63326C1E4E8DCF396243775C1AD9C3396143735B1ADFC63E66366C1E4E8D_140520261701504360E.pdf" &

echo "→ Financial Performance Q1/2026 (F45)"
curl -sL -o "$DISCLOSURE_DIR/htc-f45-q1-2026.pdf" \
  "https://hub.optiwise.io/en/documents/218971/644370581ADEC43C2A43725E1ADAC538670F015E6BD8B44B1735765669DFC23E674A755F19A9B04B644A765E1ADDC2396E316C1E4E8DCF396243775C1AD9C3396143735A1BDDCD3066366C1E4E8D_140520261701416880E.pdf" &

echo "→ AGM 2026 Minutes"
curl -sL -o "$DISCLOSURE_DIR/htc-agm2026-minutes.pdf" \
  "https://hub.optiwise.io/en/documents/216531/644370581ADEC53E2A43725E1ADAC538670F725D1FAFB74C6643745F6FAACC31604A76571AD3B44E6143075C1EADB33A134B6C1E4E8DCF386043775C1AD9C3396140755B18DDC23F66366C1E4E8D_060520261737526770E.pdf" &

echo "→ Director Change Jul 2026"
curl -sL -o "$DISCLOSURE_DIR/htc-director-change-20260703.pdf" \
  "https://hub.optiwise.io/en/documents/224573/644370581ADCC53A2A43725E1ADAC538670F735C69D9C63B1035702A6CDCCC3F134072571ADAB13D124A76286FDFB63B104B6C1E4E8DCF386543755C1AD9C3386040755E1AD9C13166366C1E4E8D_030720260637002490E.pdf" &

wait
echo "✅ Company Disclosures complete"

# ==========================================
# Summary
# ==========================================
echo ""
echo "=========================================="
echo "📊 Download Summary"
echo "=========================================="
echo ""
echo "Annual Reports: $(ls -1 "$ANNUAL_DIR"/*.pdf 2>/dev/null | wc -l) files"
du -sh "$ANNUAL_DIR"
echo ""
echo "Financial Data: $(ls -1 "$FINANCIAL_DIR"/*.pdf 2>/dev/null | wc -l) files"
du -sh "$FINANCIAL_DIR"
echo ""
echo "Company Disclosures: $(ls -1 "$DISCLOSURE_DIR"/*.pdf 2>/dev/null | wc -l) files"
du -sh "$DISCLOSURE_DIR"
echo ""
echo "✅ All downloads complete!"
