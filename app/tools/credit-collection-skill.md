# Credit Collection Skill

ใช้ตอบคำถามหนี้ค้างชำระ, overdue และ credit exposure จาก `LH_OTC_TEST.dv.mlv_credit_overdue`; ข้อมูลนี้อ่อนไหว จึงตอบเท่าที่จำเป็นต่อบทบาทผู้ใช้

## กฎ

- Helper ยืนยัน fields: `CustomerKey`, `BillingDocKey`, `BaselineDate`, `DueDate`, `AmountLC`, `SignedAmount`
- ใช้ `query_credit_and_overdue` สำหรับรายการ overdue ตาม customer หรือ due date
- คำถาม credit limit/utilization ต้อง inspect schema ของ `dv.dv_credit_use_credit_limit` ก่อน
- ทุก call ส่ง `limit=20`; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`

## Few-shot queries

### Overdue ของลูกค้า

ผู้ใช้: "หนี้ค้างของลูกค้า 0008005694"

```json
{
  "customer_key": "0008005694",
  "limit": 20,
  "page": 1
}
```

เรียก `query_credit_and_overdue`

### เอกสารที่ถึงกำหนดก่อนวันกำหนด

ผู้ใช้: "เอกสาร overdue ที่ครบกำหนดไม่เกิน 2025-06-30"

```json
{
  "due_before_date": "2025-06-30",
  "limit": 20,
  "page": 1
}
```

เรียก `query_credit_and_overdue`

### Credit utilization

ผู้ใช้: "ลูกค้าใดใช้วงเงินเกิน 80%"

ก่อน query: เรียก `get_table_schema(table_name="dv_credit_use_credit_limit", schema_name="dv", limit=20)` แล้วตรวจ field credit limit/usage ก่อนคำนวณ

## คำตอบ

ระบุ cutoff date และ source table; ไม่สรุปว่าหน้าแรก 20 แถวคือจำนวนเอกสารทั้งหมด และอย่าเปิดเผยข้อมูลเกินความจำเป็น
