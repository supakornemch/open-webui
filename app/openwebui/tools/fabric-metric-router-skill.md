# Fabric Metric Router

เลือกใช้ **เพียงหนึ่ง** focused skill ต่อคำถาม เพื่อจำกัด context และลดจำนวน tool calls:

| เจตนาของคำถาม | Skill |
|---|---|
| Net Revenue, PC/UC Volume, sales trend, breakdown | `sales-performance-skill` |
| เป้ายอดขาย Revenue/PC/UC | `sales-target-skill` |
| visit history, visit group, visit execution | `visit-execution-skill` |
| overdue, collection, credit utilization | `credit-collection-skill` |
| cooler, outlet with cooler, distribution coverage | `distribution-cooler-skill` |
| RFM segment summary | `rfm-segment-summary-skill` |
| RFM current vs previous period | `rfm-period-change-skill` |
| รายชื่อลูกค้า RFM ที่เสี่ยง | `rfm-customer-risk-skill` |

## กฎกลาง

- Database ปริยายคือ `LH_OTC_TEST`; ไม่ส่ง `database_name`
- ทุก call ส่ง `limit=20`; ห้าม `SELECT *`; ใช้ read-only `SELECT`/`WITH`
- ใช้ helper เมื่อ intent ตรง; ใช้ `query_fabric` เมื่อ aggregate หรือ breakdown
- ถ้า focused skill บอกให้ inspect schema ต้องทำก่อน ห้ามเดา field/join key
- ตอบภาษาไทยและคงชื่อ database/schema/table/column เป็นภาษาอังกฤษ
- คำถามคร่อมหลาย domain ให้ตอบ metric หลักก่อน แล้วถามว่าจะ drill down domain ที่สองหรือไม่
