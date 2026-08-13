# Sales Target Skill

ใช้ตอบคำถามเป้ายอดขาย Revenue, PC, UC ตามสินค้า, SubOrg, เดือน หรือ customer จาก `LH_OTC_TEST.dv.mlv_sale_target` และ `dv.mlv_sale_target_customer`

## กฎ

- ใช้ `query_sales_targets` สำหรับการดู target ตาม filter ที่ tool รองรับ
- Fields ที่ helper ยืนยัน: `Revenue`, `Pc`, `Uc`, `Year`, `MonthNumber`, `MaterialNo`, `PackSizeCode`, `SubOrg`; customer target เพิ่ม `CustomerKey`
- Actual vs target ต้อง inspect schema และยืนยัน grain/join key ก่อน เพราะ actual sales กับ target อาจไม่อยู่ใน grain เดียวกัน
- ทุก call ส่ง `limit=20`; ห้าม `SELECT *`; ไม่ต้องส่ง `database_name`

## Few-shot queries

### Target ตาม SubOrg และเดือน

ผู้ใช้: "เป้ายอดขายเดือน 6 ปี 2025 ของ SubOrg Z0201"

```json
{
  "year": 2025,
  "month": 6,
  "sub_org": "Z0201",
  "limit": 20,
  "page": 1
}
```

เรียก `query_sales_targets`

### Target ของสินค้า

ผู้ใช้: "เป้า Revenue ของ Material 1000001 ปี 2025"

```json
{
  "year": 2025,
  "material_no": "1000001",
  "limit": 20,
  "page": 1
}
```

เรียก `query_sales_targets`

### Target ของลูกค้า

ผู้ใช้: "เป้าลูกค้า 0008005694 เดือน 6 ปี 2025"

```json
{
  "year": 2025,
  "month": 6,
  "customer_key": "0008005694",
  "limit": 20,
  "page": 1
}
```

เรียก `query_sales_targets`

## คำตอบ

ระบุ target table, period, filter และ level ของ target; อย่าอ้าง attainment percentage จน query actual กับ target ที่ grain เดียวกันสำเร็จ
