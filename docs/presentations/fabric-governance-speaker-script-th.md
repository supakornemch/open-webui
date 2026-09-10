# บทพูดประกอบ — Fabric Data Access Governance: 3 Options

## หน้า 1 — Option A: Delegated User Token / On-Behalf-Of

หน้าแรกคือแนวทางที่เราแนะนำให้เป็นเป้าหมายสำหรับ Production ครับ แนวคิดหลักคือ สิทธิ์ของผู้ถามจะเดินทางไปถึง Microsoft Fabric ด้วยตัวตนของผู้ใช้คนนั้นจริง ๆ

เส้นทางเริ่มจากพนักงานเข้าสู่ระบบด้วย Microsoft Entra ID จากนั้น Open WebUI จะตรวจสอบกลุ่มของผู้ใช้ และจำกัดก่อนเลยว่า ผู้ใช้คนนี้สามารถมองเห็นและเรียกใช้ Skill หรือ Tool อะไรได้บ้าง ตรงนี้เป็นด่านแรกสำหรับลดพื้นที่การเข้าถึง แต่ยังไม่ใช่ด่านตัดสินสิทธิ์ข้อมูล

เมื่อผู้ใช้ส่งคำถาม ระบบจะใช้กระบวนการ On-Behalf-Of เพื่อแลก Delegated Token โดยรักษา Object ID และบริบทของผู้ใช้ไว้ตลอดเส้นทาง ก่อนส่งคำสั่งไป Fabric จะมี Query Guard ตรวจสอบว่าเข้าถึงเฉพาะ Table และ Column ที่อนุญาต เป็นคำสั่งอ่านข้อมูลเท่านั้น และมีการจำกัดปริมาณผลลัพธ์

จุดสำคัญคือ Fabric SQL Endpoint จะ Execute ด้วย User Token ไม่ใช่ Service Principal กลาง ดังนั้น Fabric สามารถบังคับใช้ SQL Role, Row-Level Security, Column Permission และ Data Masking ตามสิทธิ์ของผู้ใช้จริงได้

ข้อดีคือ Security Boundary อยู่ที่ Fabric และ Audit สามารถระบุได้ว่าใครเป็นผู้เข้าถึงข้อมูล หาก Token ของผู้ใช้มีปัญหา ระบบต้องปฏิเสธการทำงานทันที และห้าม Fallback ไปใช้ Service Principal ที่มีสิทธิ์สูงกว่า แนวทางนี้ปลอดภัยและตรวจสอบย้อนหลังได้ดีที่สุด แต่ต้องลงทุนปรับ SSO, OBO Flow และการบริหาร Token Lifecycle ครับ

## หน้า 2 — Option B: Authorization Broker + Service Principal

หน้าที่สองเป็นแนวทางสำหรับ MVP หรือ POC ที่ต้องการเริ่มได้เร็ว โดยยังใช้ Service Principal กลางในการเชื่อมต่อ Fabric

ช่วงแรกเหมือน Option A คือ ผู้ใช้ Sign in ผ่าน Entra ID และ Open WebUI จำกัด Skill กับ Tool ตาม Group ก่อน จากนั้น Authorization Broker จะนำ Object ID และ Group ที่ Backend ตรวจสอบแล้ว ไปแปลงเป็นนโยบายว่า ผู้ใช้เข้าถึง Data Product, View, Column และขอบเขตของข้อมูลใดได้บ้าง

สำหรับผู้ใช้ทั่วไป เราจะไม่เปิด Generic SQL ให้โมเดลสร้างคำสั่งได้อิสระ แต่จะใช้ Typed Data Tools ซึ่งกำหนด Input, Allowlist และ Filter ไว้ชัดเจนทุก Request โมเดลไม่มีสิทธิ์ส่ง Role หรือ Identity มาอ้างเอง

Service Principal ของ Genie จะได้รับสิทธิ์แบบ Least Privilege และอ่านได้เฉพาะ Curated Views ที่เตรียมไว้ใน Fabric เท่านั้น ส่วน Audit ต้องเก็บสองชั้น คือ Fabric จะเห็นว่า Service Principal เป็นผู้ Query ขณะที่ Application Log ต้องบันทึก Object ID ของ End User, Tool ที่เรียก, Data Object, Query Hash และจำนวนแถวที่คืนกลับมา

แนวทางนี้เปลี่ยนระบบปัจจุบันน้อยและเหมาะกับการพิสูจน์ Use Case อย่างรวดเร็ว แต่มีข้อจำกัดสำคัญ คือ Authorization Logic อยู่ที่ Application หาก Tool หรือ Policy Broker มีช่องโหว่ อาจทำให้ผู้ใช้ได้รับสิทธิ์รวมของ Service Principal ได้ ดังนั้นต้องใช้ Deny-by-Default, ปิด Generic SQL และทดสอบ Policy ทุกเส้นทางครับ

## หน้า 3 — Option C: Service Principal แยกตาม Role

หน้าสุดท้ายเป็นทางเลือกช่วงเปลี่ยนผ่าน โดยแยก Service Principal ตาม Role หรือ Business Domain เช่น Sales, Finance และ HR แทนการใช้ Service Principal ตัวเดียวร่วมกัน

ผู้ใช้ยังคงผ่าน Entra ID และ Open WebUI Skill Access Control เป็นด่านแรก จากนั้น Role Router จะอ่าน Group ที่ผ่านการตรวจสอบแล้ว และเลือก Identity ที่ตรงกับบทบาทของผู้ใช้ เช่น Sales Service Principal หรือ Finance Service Principal ก่อนส่ง Query ไปยัง Fabric

ข้อดีคือช่วยลด Blast Radius เพราะแต่ละ Identity มีสิทธิ์เฉพาะ Domain ของตนเอง หาก Credential ตัวหนึ่งมีปัญหา ผลกระทบจะไม่ขยายไปทุกข้อมูลเหมือนการใช้ Service Principal กลางตัวเดียว และ Fabric สามารถกำหนด GRANT หรือ Curated View แยกตาม Role ได้

อย่างไรก็ตาม ระบบต้องบริหาร Identity หลายตัว รวมถึง Ownership, Credential Rotation, Role Mapping และกรณีผู้ใช้มีหลายบทบาท ซึ่งจะซับซ้อนขึ้นอย่างรวดเร็ว อีกทั้ง Fabric Audit จะเห็นเพียง Role Service Principal ไม่เห็น End User ที่ถามข้อมูลจริง ทำให้ Row-Level Security รายบุคคลและการสืบค้นย้อนหลังทำได้ยากกว่า Option A

ดังนั้นข้อเสนอคือ ใช้ Option B สำหรับ MVP ที่ต้องส่งมอบเร็ว พร้อม Guardrail ที่เข้มงวด และวาง Roadmap ไป Option A สำหรับ Production ส่วน Option C ควรใช้เฉพาะกรณีที่ต้องการแยก Domain ชัดเจนในช่วงเปลี่ยนผ่าน และองค์กรพร้อมรับภาระการดูแล Identity เพิ่มขึ้นครับ