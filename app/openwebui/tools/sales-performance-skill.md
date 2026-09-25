# Sales Performance Skill

ใช้ตอบคำถามยอดขาย, Net Revenue, PC Volume, UC Volume, trend และ breakdown ตาม `SubOrg`, `Zone`, `Brand` หรือ customer จาก `LH_OTC_TEST.dv.mlv_sale_preformance_aggregate`

## กฎ

- Metric ที่ยืนยันแล้ว: `SumBillNetRevenue`, `SumBillPCVolume`, `SumBillUCVolume`, `BillingDate`, `SubOrgKey`, `Zone`, `BrandKey`, `BillCustomerKey`
- ถ้าต้องการรายการรายวัน/รายการขาย ใช้ `query_sales_performance`; ถ้าต้อง aggregate, trend, YoY หรือ breakdown ใช้ `query_fabric`
- ระบุช่วงวันแบบ inclusive-start/exclusive-end สำหรับ aggregate เช่น `>= '2025-01-01' AND < '2025-07-01'`
- ทุก call ส่ง `limit=20`; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`

## Few-shot queries

### ยอดรวมช่วงเวลา

ผู้ใช้: "ยอด Net Revenue ครึ่งแรกปี 2025 เท่าไร"

```json
{
  "sql_query": "SELECT SUM(SumBillNetRevenue) AS net_revenue FROM dv.mlv_sale_preformance_aggregate WHERE BillingDate >= '2025-01-01' AND BillingDate < '2025-07-01'",
  "limit": 20
}
```

### Trend รายเดือน

ผู้ใช้: "ยอดขายรายเดือนปี 2025"

```json
{
  "sql_query": "SELECT YEAR(BillingDate) AS sales_year, MONTH(BillingDate) AS sales_month, SUM(SumBillNetRevenue) AS net_revenue, SUM(SumBillPCVolume) AS pc_volume, SUM(SumBillUCVolume) AS uc_volume FROM dv.mlv_sale_preformance_aggregate WHERE BillingDate >= '2025-01-01' AND BillingDate < '2026-01-01' GROUP BY YEAR(BillingDate), MONTH(BillingDate) ORDER BY sales_year, sales_month",
  "limit": 20
}
```

### Breakdown ตาม Zone

ผู้ใช้: "ยอดขายเดือนมิถุนายน 2025 แยก Zone"

```json
{
  "sql_query": "SELECT Zone, SUM(SumBillNetRevenue) AS net_revenue FROM dv.mlv_sale_preformance_aggregate WHERE BillingDate >= '2025-06-01' AND BillingDate < '2025-07-01' GROUP BY Zone ORDER BY net_revenue DESC",
  "limit": 20
}
```

## คำตอบ

รายงานช่วงเวลา, metric, grain, filter และ source table; อย่าระบุหน่วยเงินจนกว่าจะมี business definition ยืนยัน
