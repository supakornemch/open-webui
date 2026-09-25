# RFM Segment Summary Skill

ใช้เมื่อผู้ใช้ถามภาพรวม RFM ของ segment เช่น จำนวนลูกค้า ค่าเฉลี่ย Frequency/Monetary/Recency หรือมูลค่ารวมของ Champion, Loyal, Need Attention และ segment อื่น ตอบภาษาไทยจากผล query จริงใน `LH_OTC_TEST.dv.mlv_customer_rfm` เท่านั้น

## กฎสั้น

- ใช้ `query_fabric` สำหรับ `COUNT`, `SUM`, `AVG` และ `GROUP BY`; อย่าดึงรายการมาคำนวณเอง
- ใช้ `adjusted_rfm_segment` เมื่อผู้ใช้ระบุชื่อกลุ่ม; ใช้ `base_rfm_segment` เฉพาะเมื่อผู้ใช้ขอ base segment
- ใช้ fields ที่ยืนยันแล้วได้ทันที: `CustomerKey`, `cur_frequency`, `cur_monetary`, `cur_recency_days`, `base_rfm_segment`, `adjusted_rfm_segment`, `RFM_score`, `segment_health`
- ส่ง `limit=20` ทุกครั้ง; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`
- อย่าระบุหน่วยเงิน หาก business definition ยังไม่ยืนยัน

## Few-shot queries

### ตัวอย่าง 1 — ค่าเฉลี่ยของ Champion

ผู้ใช้: "ลูกค้ากลุ่ม Champion มี Frequency, Monetary และ Recency เฉลี่ยเท่าไร"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT adjusted_rfm_segment, COUNT(*) AS customer_cnt, AVG(cur_frequency) AS avg_frequency, AVG(cur_monetary) AS avg_monetary, AVG(cur_recency_days) AS avg_recency_days FROM dv.mlv_customer_rfm WHERE adjusted_rfm_segment = 'Champion' GROUP BY adjusted_rfm_segment",
  "limit": 20
}
```

### ตัวอย่าง 2 — มูลค่าของ Need Attention

ผู้ใช้: "Need Attention มีลูกค้ากี่รายและมูลค่ารวมเท่าไร"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT adjusted_rfm_segment, COUNT(*) AS customer_cnt, SUM(cur_monetary) AS total_monetary, AVG(cur_monetary) AS avg_monetary FROM dv.mlv_customer_rfm WHERE adjusted_rfm_segment = 'Need Attention' GROUP BY adjusted_rfm_segment",
  "limit": 20
}
```

### ตัวอย่าง 3 — เปรียบเทียบทุก segment

ผู้ใช้: "สรุปจำนวนลูกค้าและ Monetary แยกตาม segment"

เรียก `query_fabric`:

```json
{
  "sql_query": "SELECT adjusted_rfm_segment, COUNT(*) AS customer_cnt, SUM(cur_monetary) AS total_monetary, AVG(cur_monetary) AS avg_monetary FROM dv.mlv_customer_rfm GROUP BY adjusted_rfm_segment ORDER BY total_monetary DESC",
  "limit": 20
}
```

## คำตอบ

สรุปตัวเลขก่อน ตามด้วยเงื่อนไข `adjusted_rfm_segment`, source table และข้อจำกัดเรื่องหน่วย/NULL แยกข้อเท็จจริงจากข้อเสนอแนะเสมอ
