# Distribution and Cooler Skill

ใช้ตอบคำถามร้านที่มีตู้แช่, การซื้อของ outlet ที่มี cooler, cooler placement และ distribution coverage

## กฎ

- ใช้ `query_coolers` สำหรับร้านที่มี cooler และ buying data; helper ยืนยัน fields `EquipmentKey`, `CustomerKey`, `ValidFromDate`, `ValidToDate`, `StorageLocationKey`, `BillCustomerKey`, `BillingDate`
- การค้นหา serial/status ต้อง inspect `dv.dv_cooler` ก่อนแล้วใช้ `query_fabric`; helper ไม่รองรับ filter สองตัวนี้
- Distribution coverage/target ต้อง inspect `dv.mlv_distributed_outlets_customer` หรือ `dv.dv_distribution_target` ก่อน
- ทุก call ส่ง `limit=20`; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`

## Few-shot queries

### ร้านที่มีตู้และซื้อสินค้า

ผู้ใช้: "ร้าน 0008005694 ที่มีตู้แช่และมีการซื้อ"

```json
{
  "customer_key": "0008005694",
  "limit": 20,
  "page": 1
}
```

เรียก `query_coolers`

### รายการ outlet with cooler ล่าสุด

ผู้ใช้: "แสดงร้านมีตู้แช่ที่มีการซื้อล่าสุด"

```json
{
  "limit": 20,
  "page": 1
}
```

เรียก `query_coolers`

### ค้นหาตู้ด้วย serial

ผู้ใช้: "ค้นหาตู้ serial ABC123"

ก่อน query: เรียก `get_table_schema(table_name="dv_cooler", schema_name="dv", limit=20)` ก่อน แล้วใช้ `query_fabric` โดยเลือกเฉพาะ serial/equipment/customer fields ที่ schema ยืนยัน

## คำตอบ

ระบุว่าเป็น cooler-buying relation หรือ asset master, ช่วงเวลา/สถานะความถูกต้อง และจำนวนสูงสุด 20 แถว
