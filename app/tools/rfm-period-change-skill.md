# RFM Period Change Skill

ใช้เมื่อผู้ใช้ถามการเติบโต/ลดลง เปรียบเทียบ current กับ previous period, segment ที่สูญเสียมูลค่า หรือ growth percentage จาก `LH_OTC_TEST.dv.mlv_customer_rfm`

## กฎสั้น

- ใช้ `query_fabric` และคำนวณ aggregate/percentage ใน SQL เท่านั้น
- Fields ที่ใช้: `cur_monetary`, `py_monetary`, `cur_frequency`, `py_frequency`, `adjusted_rfm_segment`
- `cur_*`/`py_*` คือ current/previous period ตาม pipeline; ห้ามเรียกว่า 2025/2024 หรือ YoY จนมี metadata ยืนยัน
- Percentage ต้องใช้ `NULLIF(previous_value, 0)` และกรอง previous value ให้มากกว่า 0
- ส่ง `limit=20`; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`

## Few-shot queries

### ตัวอย่าง 1 — Champion ที่มูลค่าลดเกิน 30%

ผู้ใช้: "มี Champion กี่รายที่ยอดขายลดจากช่วงก่อนมากกว่า 30%"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT COUNT(*) AS customer_cnt FROM dv.mlv_customer_rfm WHERE adjusted_rfm_segment = 'Champion' AND py_monetary > 0 AND cur_monetary < py_monetary * 0.70",
  "limit": 20
}
```

### ตัวอย่าง 2 — Segment ที่สูญเสียมูลค่ามากที่สุด

ผู้ใช้: "segment ไหนสูญเสียรายได้มากที่สุด"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT adjusted_rfm_segment, SUM(py_monetary) AS previous_monetary, SUM(cur_monetary) AS current_monetary, SUM(cur_monetary - py_monetary) AS monetary_diff FROM dv.mlv_customer_rfm GROUP BY adjusted_rfm_segment ORDER BY monetary_diff ASC",
  "limit": 20
}
```

### ตัวอย่าง 3 — Segment โตเกิน 10%

ผู้ใช้: "segment ใดเติบโตเกิน 10% จากช่วงก่อน"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT adjusted_rfm_segment, SUM(py_monetary) AS previous_monetary, SUM(cur_monetary) AS current_monetary, (SUM(cur_monetary) - SUM(py_monetary)) * 100.0 / NULLIF(SUM(py_monetary), 0) AS growth_pct FROM dv.mlv_customer_rfm GROUP BY adjusted_rfm_segment HAVING SUM(py_monetary) > 0 AND (SUM(cur_monetary) - SUM(py_monetary)) * 100.0 / NULLIF(SUM(py_monetary), 0) > 10 ORDER BY growth_pct DESC",
  "limit": 20
}
```

## คำตอบ

ใช้คำว่า current period/previous period จนกว่าช่วงเวลาจะได้รับการยืนยัน รายงานสูตร threshold, source table และ zero-denominator พร้อมผลลัพธ์
