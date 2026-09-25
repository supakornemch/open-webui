# RFM Customer Risk Skill

ใช้เมื่อผู้ใช้ต้องการรายชื่อลูกค้าเสี่ยง เช่น มูลค่าลดลง Frequency ลดลง ไม่ซื้อนาน หรือ Champion/Loyal ที่ควรติดตาม จาก `LH_OTC_TEST.dv.mlv_customer_rfm`

## กฎสั้น

- ใช้ `query_fabric`; คืนเฉพาะ fields ที่จำเป็นและไม่เกิน 20 ราย
- ใช้ `CustomerKey` เป็น identifier เริ่มต้น ไม่ join ชื่อลูกค้าเว้นแต่ผู้ใช้ขอชื่อ
- หากผู้ใช้ขอชื่อ ให้ตรวจ schema/join key ก่อน แล้วจึง join `gold.dim_customer`; ห้ามเดา
- Percentage ต้องใช้ `NULLIF(previous_value, 0)` และกรอง previous value ให้มากกว่า 0
- `cur_*`/`py_*` หมายถึง current/previous period ตาม pipeline ไม่ใช่ปีปฏิทินโดยอัตโนมัติ
- ทุก query รายชื่อต้องมี deterministic `ORDER BY`, ส่ง `limit=20`, ห้าม `SELECT *`, และไม่ต้องส่ง `database_name`

## Few-shot queries

### ตัวอย่าง 1 — Need Attention มูลค่าสูงแต่ลดเกิน 20%

ผู้ใช้: "Need Attention รายใดเคยมียอดเกิน 100,000 แต่ลดลงมากกว่า 20%"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT CustomerKey, adjusted_rfm_segment, py_monetary, cur_monetary, cur_monetary - py_monetary AS monetary_diff, (py_monetary - cur_monetary) * 100.0 / NULLIF(py_monetary, 0) AS decline_pct FROM dv.mlv_customer_rfm WHERE adjusted_rfm_segment = 'Need Attention' AND py_monetary >= 100000 AND cur_monetary <= py_monetary * 0.80 ORDER BY py_monetary DESC, CustomerKey ASC",
  "limit": 20
}
```

### ตัวอย่าง 2 — Frequency ลดเกิน 95%

ผู้ใช้: "ลูกค้ารายใด Frequency ลดลงเกิน 95%"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT CustomerKey, adjusted_rfm_segment, py_frequency, cur_frequency, (py_frequency - cur_frequency) * 100.0 / NULLIF(py_frequency, 0) AS decline_pct FROM dv.mlv_customer_rfm WHERE py_frequency > 0 AND cur_frequency <= py_frequency * 0.05 ORDER BY decline_pct DESC, CustomerKey ASC",
  "limit": 20
}
```

### ตัวอย่าง 3 — Champion/Loyal ที่เสี่ยงหลุด

ผู้ใช้: "Champion หรือ Loyal ที่ไม่ซื้อมากกว่า 45 วันและ Frequency ลดเกิน 80%"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT CustomerKey, adjusted_rfm_segment, cur_recency_days, py_frequency, cur_frequency, (py_frequency - cur_frequency) * 100.0 / NULLIF(py_frequency, 0) AS decline_pct FROM dv.mlv_customer_rfm WHERE adjusted_rfm_segment IN ('Champion', 'Loyal') AND cur_recency_days > 45 AND py_frequency > 0 AND cur_frequency <= py_frequency * 0.20 ORDER BY cur_recency_days DESC, decline_pct DESC, CustomerKey ASC",
  "limit": 20
}
```

## คำตอบ

บอกว่าเป็น Top 20/หน้าแรก ไม่ใช่ลูกค้าทั้งหมด ระบุ segment, threshold, current/previous period, source table และข้อจำกัดเรื่องชื่อหรือหน่วย
