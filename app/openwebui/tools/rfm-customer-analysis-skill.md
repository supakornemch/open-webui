# RFM Analysis Router

เลือกอ่าน **เพียงหนึ่ง** skill ต่อคำถาม RFM เพื่อให้ query เร็วและ context เล็กลง:

| เจตนาของคำถาม | Skill ที่ใช้ |
|---|---|
| จำนวนลูกค้า, ค่าเฉลี่ย, มูลค่ารวม, สรุปหรือเปรียบเทียบ segment | `rfm-segment-summary-skill.md` |
| current vs previous period, growth, decline, segment ที่เสียมูลค่า | `rfm-period-change-skill.md` |
| รายชื่อลูกค้าเสี่ยง, ไม่ซื้อนาน, Frequency/Monetary ลด, รายที่ต้องติดตาม | `rfm-customer-risk-skill.md` |

## กฎกลาง

- ใช้ข้อมูลจริงจาก `LH_OTC_TEST.dv.mlv_customer_rfm` เท่านั้น
- ส่ง `limit=20`, ห้าม `SELECT *`, และไม่ต้องส่ง `database_name`
- ถ้าต้องใช้ field หรือ join ที่ไม่มีใน skill ที่เลือก ให้เรียก `get_table_schema` ก่อน
- ตอบภาษาไทย โดยเก็บ database/schema/table/column เป็นภาษาอังกฤษ
- หากคำถามมีทั้ง summary และรายชื่อลูกค้า ให้ตอบ aggregate ก่อน แล้วเลือก skill รายชื่อสำหรับ call ถัดไป