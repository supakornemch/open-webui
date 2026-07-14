# Haadthip Investor Relations (IR) Documents

เอกสารจากเว็บไซต์ Haad Thip Investor Relations สำหรับใช้เป็น **Agentic Knowledge Source** ในระบบ Enterprise Chat

> **Source:** https://www.haadthip.com/en/investor-relations/home
> **Downloaded:** 2026-07-06
> **Total:** 31 ไฟล์, ~274 MB

## Directory Structure

```
haadthip-investor-relations/
├── README.md
├── 01-annual-reports/        Annual Reports / Form 56-1 One Report (24 ไฟล์)
├── 02-financial-data/        Financial Statements, Fact Sheets (2 ไฟล์)
└── 03-company-disclosures/   Company Disclosures, Press Releases (5 ไฟล์)
```

## 1. Annual Reports (`01-annual-reports/`) — 24 ไฟล์

### One Report (Form 56-1) — ฉบับสมบูรณ์

| ปี | ไฟล์ EN | ไฟล์ TH (Form 56-1) | ขนาด |
|:--:|---------|---------------------|:----:|
| 2025 | `htc-one-report2025-en.pdf` | — | 29 MB |
| 2025 | `htc-e-one-report2025-en.pdf` (e-report) | — | 25 MB |
| 2024 | `htc-e-one-report2024-en.pdf` (e-report) | — | 2.6 MB |
| 2023 | `htc-one-report2023-en.pdf` | — | 39 MB |
| 2022 | `htc-one-report2022-en.pdf` | — | 6.2 MB |
| 2021 | `htc-one-report2021-en.pdf` | — | 6.1 MB |
| 2020 | `htc-ar2020-en.pdf` | `htc-form561-2020-th.pdf` | 4.6 MB |
| 2019 | `htc-ar2019-en.pdf` | `htc-form561-2019-th.pdf` | 3.5 MB |
| 2018 | `htc-ar2018-en.pdf` | `htc-form561-2018-th.pdf` | 4.0 MB |
| 2017 | `htc-ar2017.pdf` | `htc-form561-2017.pdf` | 24 MB |
| 2016 | `htc-ar2016-en.pdf` | `htc-form561-2016.pdf` | 2.9 MB |
| 2015 | `htc-ar2015-en.pdf` | `htc-form561-2015.pdf` | 8.3 MB |
| 2014 | `htc-ar2014-en.pdf` | `htc-form561-2014.pdf` | 6.1 MB |
| 2013 | `htc-ar2013-en.pdf` | `htc-form561-2013.pdf` | 5.5 MB |
| 2012 | `htc-ar2012-en.pdf` | `htc-form561-2012.pdf` | 5.3 MB |

> **หมายเหตุ:** One Report 2024 (หลัก) มีอยู่แล้วใน `documents/haadthip-corporate/05-public-disclosure/` (file: `htc-one-report-2024-en.pdf`)

### Content ที่มีใน One Report
- ข้อมูลบริษัทและธุรกิจ
- ผลการดำเนินงานทางการเงิน
- โครงสร้างองค์กรและการกำกับดูแล
- ความเสี่ยงและการบริหารจัดการ
- ESG / ความยั่งยืน
- งบการเงิน

## 2. Financial Data (`02-financial-data/`) — 2 ไฟล์

| ไฟล์ | รายละเอียด | ขนาด |
|------|-----------|:----:|
| `htc-earning-results-q1-2026.pdf` | ผลประกอบการ Q1/2026 (13 หน้า) | 3.1 MB |
| `htc-factsheet-3m2026.pdf` | Fact Sheet ไตรมาส 1/2026 (37 MB) | 37 MB |

## 3. Company Disclosures (`03-company-disclosures/`) — 5 ไฟล์

| ไฟล์ | รายละเอียด | วันที่ | ขนาด |
|------|-----------|:----:|:----:|
| `htc-mda-q1-2026.pdf` | MD&A Q1/2026 (Management Discussion & Analysis) | 14 May 2026 | 308 KB |
| `htc-agm2026-minutes.pdf` | รายงานการประชุม AGM 2026 | 06 May 2026 | 135 KB |
| `htc-f45-q1-2026.pdf` | Financial Performance Q1/2026 (F45) | 14 May 2026 | 35 KB |
| `htc-director-change-20260703.pdf` | เปลี่ยนแปลงกรรมการบริษัท | 03 Jul 2026 | 33 KB |
| `htc-pr-2023-earning-results.pdf` | Press Release — ผลประกอบการ 2023 | 01 Mar 2024 | 140 KB |

## ความเหมาะสมเป็น Agentic Knowledge Source

### 📊 สำหรับ QA เกี่ยวกับธุรกิจ (แนะนำมากที่สุด)
1. **One Report 2025** — ข้อมูลล่าสุด ครอบคลุมทุกด้าน (29 MB)
2. **Earning Results Q1/2026** — ข้อมูลการเงินไตรมาสล่าสุด
3. **Fact Sheet 3M/2026** — ภาพรวมผลประกอบการ

### 📈 สำหรับข้อมูลย้อนหลัง
- One Report 2012-2024 — ดูแนวโน้ม和历史 performance
- Form 56-1 (TH) — ข้อมูลตามแบบ filing ของ ก.ล.ต.

### 📰 สำหรับข่าวสารล่าสุด
- MD&A, F45, AGM Minutes — การเปิดเผยข้อมูลล่าสุด
- Press Releases — ประวัติข่าวประชาสัมพันธ์

## การนำเข้า AI Search

แนะนำให้สร้าง:
1. **Blob Container:** `haadthip-investor-relations` (หรือใช้ container เดิม)
2. **Data Source:** `haadthip-investor-relations-ds`
3. **Index:** `haadthip-investor-relations-idx`
4. **Skillset:** `haadthip-investor-relations-skillset` (Document Extraction)
5. **Indexer:** `haadthip-investor-relations-idxr`
6. **Knowledge Source:** `haadthip-investor-relations-ks`
7. **Knowledge Base:** เพิ่มเข้า `haadthip-kb` (พร้อมกับ existing KS)

## Download Script

ดู `scripts/download-ir-docs.sh` สำหรับ re-download ถ้าต้องการอัปเดตภายหลัง
