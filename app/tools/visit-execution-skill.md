# Visit Execution Skill

ใช้ตอบคำถามแผน/ประวัติเยี่ยมลูกค้า ตามช่วงเวลา, customer, SubOrg และ visit group จาก `LH_OTC_TEST.dv.mlv_customer_visit_list`

## กฎ

- ใช้ `query_customer_visits` สำหรับรายการ visit; helper ยืนยัน fields `ExecDateKey`, `SubOrgKey`, `CustomerKey`, `VisitGroupKey`, `GroupVisitKey`
- คำถาม visit rate, no-visit หรือ visit-to-order ต้อง inspect schema ของ `dv.mlv_customer_visit_sales_order` หรือ `dv.dv_visit_so` ก่อน
- ทุก call ส่ง `limit=20`; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`

## Few-shot queries

### ประวัติเยี่ยมลูกค้า

ผู้ใช้: "ประวัติเยี่ยมลูกค้า 0008005694 ในเดือนมิถุนายน 2025"

```json
{
  "customer_key": "0008005694",
  "visit_date_from": "2025-06-01",
  "visit_date_to": "2025-06-30",
  "limit": 20,
  "page": 1
}
```

เรียก `query_customer_visits`

### รายการตาม visit group

ผู้ใช้: "แสดง visit group VG001 เดือนมิถุนายน 2025"

```json
{
  "visit_group_key": "VG001",
  "visit_date_from": "2025-06-01",
  "visit_date_to": "2025-06-30",
  "limit": 20,
  "page": 1
}
```

เรียก `query_customer_visits`

### Visit-to-order KPI

ผู้ใช้: "visit-to-order rate เดือนมิถุนายน 2025"

ก่อน query: เรียก `get_table_schema(table_name="mlv_customer_visit_sales_order", schema_name="dv", limit=20)` แล้วใช้เฉพาะ column ที่ยืนยันใน schema

## คำตอบ

ระบุว่าเป็นรายการสูงสุด 20 แถวหรือ aggregate จริง, ช่วงวัน, filter และ source table
