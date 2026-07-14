#!/usr/bin/env python3
"""
flatten-eexpense-qa.py — Parse E-Expense Q&A Excel and flatten Decision Tree → FAQ JSONL
==========================================================================================

Traces every path through the decision tree, builds enriched FAQ docs with:
  - Root question as main topic
  - Branching choices as conditions
  - Breadcrumb trail as contextQuestions
  - Category, keywords, shortAnswer

Output: data/eexpense-faq.jsonl
Usage: python3 scripts/flatten-eexpense-qa.py [--excel path/to/file.xlsx]
"""

import json, re, sys, argparse, hashlib
from pathlib import Path
from collections import defaultdict

try:
    import pandas as pd
except ImportError:
    print("❌ pandas required: pip install pandas openpyxl")
    sys.exit(1)

DEFAULT_EXCEL = str(Path(__file__).parent.parent / "docs" / "Q&A สำหรับ chatbot_E-Expense.xlsx")
OUTPUT_JSONL = str(Path(__file__).parent.parent / "data" / "eexpense-faq.jsonl")

# ── Answer enrichments ─────────────────────────────────
# Maps ANS id → {category, keywords, shortAnswer}
ANSWER_META = {
    "ANS1": {
        "category": "การขอทดรองจ่าย",
        "shortAnswer": "ต้องขอล่วงหน้าอย่างน้อย 3 วันไม่รวมวันหยุด",
        "keywords": ["ทดรองจ่าย", "ล่วงหน้า", "3 วัน", "ขอแผน", "เดินทาง"],
    },
    "ANS2": {
        "category": "การขอทดรองจ่าย",
        "shortAnswer": "ไม่มีกำหนดเวลา ขอก่อนหรือย้อนหลังก็ได้",
        "keywords": ["ไม่มีทดรอง", "ไม่มีกำหนด", "ย้อนหลัง", "ขอแผน", "เดินทาง"],
    },
    "ANS3": {
        "category": "การขอทดรองจ่าย",
        "shortAnswer": "ต้องขอล่วงหน้า 3 วัน ไม่รวมวันหยุด ไม่สามารถขอย้อนหลังได้",
        "keywords": ["ทดรองจ่าย", "ย้อนหลังไม่ได้", "3 วัน", "ขอแผน", "เดินทาง"],
    },
    "ANS4": {
        "category": "แผนการเดินทาง",
        "shortAnswer": "ขออนุมัติแผนการเดินทางย้อนหลังเพื่อเคลียร์ค่าใช้จ่ายได้",
        "keywords": ["ย้อนหลัง", "เคลียร์ค่าใช้จ่าย", "ขอแผน", "เดินทาง", "ไม่มีทดรอง"],
    },
    "ANS5": {
        "category": "แผนการเดินทาง",
        "shortAnswer": "ต้องขอแผนการเดินทางเสมอแม้เป็น One-day trip",
        "keywords": ["one-day trip", "เช้าเย็นกลับ", "เอกสารเดินทาง", "ขอแผน", "ต่างจังหวัด"],
    },
    "ANS6": {
        "category": "ผู้ร่วมเดินทาง",
        "shortAnswer": "ทำเอกสารรวมกันได้ โดยผู้ขอเบิกควรเป็น Level สูงสุด",
        "keywords": ["ผู้ร่วมเดินทาง", "Cost Center เดียวกัน", "รวมกัน", "ขอแผน", "Level"],
    },
    "ANS7": {
        "category": "ผู้ร่วมเดินทาง",
        "shortAnswer": "ต้องสร้างเอกสารขอแผนแยกกัน เมื่อใช้คนละ Cost Center",
        "keywords": ["ผู้ร่วมเดินทาง", "คนละ Cost Center", "แยกกัน", "ขอแผน", "ต่างงบ"],
    },
    "ANS8": {
        "category": "สิทธิ์การเบิก",
        "shortAnswer": "เฉพาะพนักงานในสังกัด HTC เท่านั้น",
        "keywords": ["สัญญาจ้าง", "Outsource", "สิทธิ์", "HTC", "เบิกค่าเดินทาง"],
    },
    "ANS9": {
        "category": "การอนุมัติ",
        "shortAnswer": "สายอนุมัติอ้างอิงจาก MyHR ตามงบประมาณอำนาจอนุมัติ",
        "keywords": ["ผู้อนุมัติ", "Approver", "MyHR", "สายอนุมัติ", "งบประมาณ"],
    },
    "ANS10": {
        "category": "การอนุมัติ",
        "shortAnswer": "แจ้ง IT Service ระบุผู้อนุมัติ ผู้รับมอบ วันที่มีผล",
        "keywords": ["Delegate", "มอบอำนาจ", "ผู้อนุมัติ", "IT Service", "อนุมัติแทน"],
    },
    "ANS11": {
        "category": "Cost Center",
        "shortAnswer": "ตรวจสอบกับ HR; หาก MyHR ถูกต้องให้แจ้ง IT Service",
        "keywords": ["Cost Center", "MyHR", "HR", "IT Service", "แก้ไขข้อมูล"],
    },
    "ANS12": {
        "category": "แผนการเดินทาง",
        "shortAnswer": "แก้ไขในใบเคลียร์ค่าใช้จ่าย หรือสร้างใบขอแผนใหม่หากเลยวันที่",
        "keywords": ["แก้ไขวันที่", "ใบขอแผน", "เคลียร์ค่าใช้จ่าย", "เดินทาง"],
    },
    "ANS13": {
        "category": "การแก้ไข/ยกเลิกเอกสาร",
        "shortAnswer": "สร้างใบเคลียร์ฯ → อ้างอิงใบทดรอง → ปิด Toggle แต่ละรายการ",
        "keywords": ["ยกเลิก", "Cancel Trip", "เคลียร์ค่าใช้จ่าย", "ทดรองจ่าย",
                      "Toggle"],
    },
    "ANS14": {
        "category": "การแก้ไข/ยกเลิกเอกสาร",
        "shortAnswer": "กดปุ่ม Terminate มุมขวาล่างในหน้า 'ภาพรวม' ของเอกสาร",
        "keywords": ["ยกเลิก", "Terminate", "Cancel Trip", "เอกสารขอแผน",
                      "ภาพรวม"],
    },
    "ANS15": {
        "category": "การแก้ไข/ยกเลิกเอกสาร",
        "shortAnswer": "กด Withdraw (สถานะยังไม่ Completed) → ระบุเหตุผล → แก้ไข → Submit ใหม่",
        "keywords": ["Withdraw", "แก้ไข", "Submit", "ขอแผนการเดินทาง", "อนุมัติใหม่"],
    },
    "ANS16": {
        "category": "การแก้ไข/ยกเลิกเอกสาร",
        "shortAnswer": "กด Withdraw หากสถานะ Wait for Requestor Accept/Approver Approve",
        "keywords": ["Withdraw", "แก้ไข", "Submit", "ขอทดรองจ่าย",
                      "เคลียร์ค่าใช้จ่าย"],
    },
    "ANS17": {
        "category": "การแก้ไข/ยกเลิกเอกสาร",
        "shortAnswer": "Withdraw กรณี Wait for Approve/HR Verify; แจ้งบัญชี Reject กรณี Wait for Accountant",
        "keywords": ["Withdraw", "แก้ไข", "Submit", "Reject", "รักษาพยาบาล",
                      "บัญชี"],
    },
    "ANS18": {
        "category": "ประวัติเอกสาร",
        "shortAnswer": "เมนู User > User Inbox (ทั้งหมด) หรือ User > User History (แยกประเภท)",
        "keywords": ["ประวัติ", "History", "Inbox", "เมนู User", "เอกสารย้อนหลัง"],
    },
    "ANS19": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 1: กรุงเทพ/ภูเก็ต/สมุย 290บ. | ต่างจังหวัดอื่น 250บ.",
        "keywords": ["Level 1", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "290",
                      "250"],
    },
    "ANS20": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 2: กรุงเทพ/ภูเก็ต/สมุย 310บ. | ต่างจังหวัดอื่น 260บ.",
        "keywords": ["Level 2", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "310",
                      "260"],
    },
    "ANS21": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "ต้องหักค่าอาหารเช้าออกหากโรงแรมมีอาหารเช้าฟรี",
        "keywords": ["โรงแรม", "อาหารเช้า", "หัก", "ค่าอาหาร", "เคลียร์ค่าใช้จ่าย"],
    },
    "ANS22": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "อัตราค่าอาหารตามระเบียบบริษัท ไม่มีอัตราพิเศษวันหยุด",
        "keywords": ["วันหยุด", "เสาร์อาทิตย์", "อัตราพิเศษ", "ค่าอาหาร",
                      "ระเบียบบริษัท"],
    },
    "ANS23": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "เบิกตามอัตราระเบียบบริษัท ไม่ต้องใช้ใบเสร็จ",
        "keywords": ["ใบเสร็จ", "ค่าอาหาร", "แยกคีย์", "รายคน", "ระเบียบบริษัท"],
    },
    "ANS24": {
        "category": "แผนการเดินทาง",
        "shortAnswer": "เคลียร์ค่าใช้จ่ายได้ทั้งแอดมินผู้สร้างเอกสารและ Requestor",
        "keywords": ["แอดมิน", "เคลียร์ค่าใช้จ่าย", "Requestor", "ผู้สร้างเอกสาร"],
    },
    "ANS25": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "เบิกค่าอาหารได้ไม่เกินอัตราที่บริษัทกำหนดเท่านั้น",
        "keywords": ["ค่าอาหารเกิน", "ทดรองจ่าย", "ส่วนต่าง", "อัตราที่กำหนด"],
    },
    "ANS26": {
        "category": "ข้อมูลระบบ",
        "shortAnswer": "ใช้สำหรับค่าใช้จ่ายเดินทาง + ทดรองจ่าย + เคลียร์ฯ + ค่ารักษาพยาบาล",
        "keywords": ["E-Expense", "ระบบ", "ค่าใช้จ่าย", "เดินทาง", "รักษาพยาบาล"],
    },
    "ANS27": {
        "category": "ข้อมูลระบบ",
        "shortAnswer": "9 ประเภท: ค่าอาหารใน/นอกประเทศ, ที่พัก, ยานพาหนะ, ซักรีด, น้ำมัน, อบรม, เลี้ยงรับรอง(เร็วๆนี้), อื่นๆ",
        "keywords": ["ค่าใช้จ่าย", "ประเภท", "ค่าอาหาร", "ค่าที่พัก", "ค่ายานพาหนะ",
                      "ซักรีด", "น้ำมัน", "อบรม"],
    },
    "ANS28": {
        "category": "สิทธิ์การเบิก",
        "shortAnswer": "ทำแทนได้ แต่ Requestor ต้องกด Accept ก่อนส่งให้ผู้อนุมัติ",
        "keywords": ["ทำเอกสารแทน", "ผู้ขอเบิก", "Requestor", "Accept", "อนุมัติ"],
    },
    "ANS29": {
        "category": "Cost Center",
        "shortAnswer": "ดึงจาก AD User อัตโนมัติ สามารถแก้ไขได้ตอนสร้างเอกสาร",
        "keywords": ["Cost Center", "AD User", "อัตโนมัติ", "ดึงข้อมูล", "แก้ไข"],
    },
    "ANS30": {
        "category": "สิทธิ์การเบิก",
        "shortAnswer": "จำเป็นต้องอยู่ในรายชื่อผู้ร่วมเดินทางเสมอ ลบออกไม่ได้",
        "keywords": ["ผู้ขอเบิก", "Requestor", "ผู้ร่วมเดินทาง", "บังคับ", "รายชื่อ"],
    },
    "ANS31": {
        "category": "ไฟล์แนบ",
        "shortAnswer": "jpg, png, tif, pdf, xml, ppt, docx, excel",
        "keywords": ["ไฟล์แนบ", "jpg", "png", "tif", "pdf", "xml", "ppt", "docx",
                      "excel"],
    },
    "ANS32": {
        "category": "ไฟล์แนบ",
        "shortAnswer": "ขนาดไม่เกิน 2 MB ต่อ 1 ไฟล์",
        "keywords": ["ไฟล์แนบ", "ขนาด", "2 MB", "สูงสุด"],
    },
    "ANS34": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 3: กรุงเทพ/ภูเก็ต/สมุย 350บ. | ต่างจังหวัดอื่น 310บ.",
        "keywords": ["Level 3", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "350",
                      "310"],
    },
    "ANS35": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 4: กรุงเทพ/ภูเก็ต/สมุย 480บ. | ต่างจังหวัดอื่น 410บ.",
        "keywords": ["Level 4", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "480",
                      "410"],
    },
    "ANS36": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 5: กรุงเทพ/ภูเก็ต/สมุย 480บ. | ต่างจังหวัดอื่น 410บ.",
        "keywords": ["Level 5", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "480",
                      "410"],
    },
    "ANS37": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 6: ทุกจังหวัด รวม 720บ./วัน",
        "keywords": ["Level 6", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "720"],
    },
    "ANS38": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 7: ทุกจังหวัด รวม 720บ./วัน",
        "keywords": ["Level 7", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ", "720"],
    },
    "ANS39": {
        "category": "ค่าอาหาร/เบี้ยเลี้ยง",
        "shortAnswer": "Level 8: ทุกจังหวัด ไม่จำกัดวงเงิน",
        "keywords": ["Level 8", "ค่าอาหาร", "เบี้ยเลี้ยง", "ในประเทศ",
                      "ไม่จำกัดวงเงิน"],
    },
}

# ── Question registry ──────────────────────────────────
QUESTION_TEXT = {
    "Q1": "ต้องคีย์ขอแผนการเดินทางล่วงหน้าอย่างน้อยกี่วัน",
    "Q2": "มีขอทดรองจ่ายหรือไม่",
    "Q3": "ขอแผนการเดินทางย้อนหลังได้หรือไม่",
    "Q4": "มีขอทดรองจ่ายหรือไม่",
    "Q5": "ไปทำงานต่างจังหวัดแบบเช้าเย็นกลับ (One-day trip) ต้องทำเอกสารเดินทางไหม",
    "Q6": "มีผู้ร่วมเดินทางไปด้วย ต้องทำเอกสารแยกกันทุกคนไหม หรือทำรวมกันใบเดียว",
    "Q7": "ผู้ร่วมเดินทางอยู่ Cost Center เดียวกันหรือไม่",
    "Q8": "ใช้งบเดินทางของ Cost Center เดียวกันหรือไม่",
    "Q9": "ถ้าผู้ร่วมเดินทางอยู่คนละแผนก/คนละสังกัด ต้องแยกใบงานไหม",
    "Q10": "พนักงานสัญญาจ้าง / Outsource มีสิทธิ์เบิกค่าเดินทางในระบบนี้ไหม",
    "Q11": "ใครเป็นผู้อนุมัติ (Approver) เอกสาร",
    "Q12": "ถ้าผู้อนุมัติไม่อยู่ สามารถตั้งผู้รับมอบอำนาจ (Delegate) มาอนุมัติแทนได้ไหม",
    "Q13": "ข้อมูล Cost Center ไม่ถูกต้อง แก้ไขยังไง",
    "Q14": "ใบขอแผนการเดินทางที่อนุมัติแล้ว สามารถแก้ไขวันที่เดินทางทีหลังได้ไหม",
    "Q15": "ถ้ายกเลิกการเดินทาง (Cancel Trip) ต้องไปกดปุ่มไหนในระบบ",
    "Q16": "มีขอทดรองจ่ายหรือไม่",
    "Q17": "คีย์ข้อมูลผิดแล้วกด submit ไปแล้ว สามารถดึงใบงานกลับมาแก้ไขได้ไหม",
    "Q18": "ดูประวัติเอกสารที่เคยสร้างย้อนหลังได้ที่เมนูไหน",
    "Q21": "หากโรงแรมที่พักมีอาหารเช้าให้ฟรี ต้องหักยอดค่าอาหารรายวันออกไหม",
    "Q22": "เดินทางไปทำงานในวันหยุดเสาร์-อาทิตย์ ได้อัตราค่าอาหารพิเศษไหม",
    "Q23": "ถ้าร้านค้าแยกใบเสร็จค่าอาหารมาให้รายคน พนักงานแยกกันคีย์เบิกเองได้ไหม",
    "Q24": "แอดมินเป็นคนคีย์ขอแผนเดินทางให้ทีม เวลาเคลียร์ค่าใช้จ่ายต้องให้แอดมินคีย์หรือพนักงานคีย์เอง",
    "Q25": "ถ้าใช้เงินค่าอาหารเกินกว่าเงินทดรองจ่ายที่ยืมไป สามารถเบิกเพิ่มส่วนต่างได้ไหม",
    "Q26": "ระบบ E-Expense ใช้ทำอะไร",
    "Q27": "ระบบรองรับค่าใช้จ่ายประเภทใดบ้าง",
    "Q28": "สามารถทำเอกสารแทนผู้อื่นได้หรือไม่",
    "Q29": "Cost Center ดึงมาจากไหน",
    "Q30": "ผู้ขอเบิกจำเป็นต้องอยู่ในรายชื่อผู้ร่วมเดินทางหรือไม่",
    "Q31": "ระบบรองรับไฟล์แนบประเภทใด",
    "Q32": "ไฟล์แนบมีขนาดสูงสุดเท่าไร",
    "Q33": "ค่าอาหารในประเทศคำนวณอย่างไร",
    "Q34": "ค่าอาหารในประเทศสิทธิ์การเบิกเท่าไหร่",
    "Q35": "พนักงาน Level อะไร",
}


def parse_excel(filepath: str) -> tuple[dict, dict, list]:
    df_q = pd.read_excel(filepath, sheet_name="คำถาม")
    df_a = pd.read_excel(filepath, sheet_name="คำตอบ")

    answers = {}
    for _, row in df_a.iterrows():
        aid = str(row["ID คำตอบ"]).strip() if pd.notna(row["ID คำตอบ"]) else None
        txt = str(row["ข้อความของบอท"]).strip() if pd.notna(row["ข้อความของบอท"]) else None
        if aid and aid.startswith("ANS") and txt and txt != "nan":
            answers[aid] = txt

    nodes = {}
    current_node = None
    all_qids = []

    for _, row in df_q.iterrows():
        qid = str(row["ID คำถาม"]).strip() if pd.notna(row["ID คำถาม"]) else None
        question = str(row["ข้อความของบอท"]).strip() if pd.notna(row["ข้อความของบอท"]) else None
        choice_type = str(row["ประเภทตัวเลือก"]).strip() if pd.notna(row["ประเภทตัวเลือก"]) else None
        choice_key = str(row["ตัวเลือกคีย์ข้อมูล"]).strip() if pd.notna(row["ตัวเลือกคีย์ข้อมูล"]) else None
        go_to = str(row["ถัดไป (Go to)"]).strip() if pd.notna(row["ถัดไป (Go to)"]) else None

        if qid and qid.startswith("Q") and question and question != "nan":
            current_node = qid
            all_qids.append(qid)
            ctype = choice_type if choice_type and choice_type not in ("-", "nan") else None
            nodes[qid] = {"question": question, "choice_type": ctype, "choices": []}

            if ctype is None:
                if go_to and go_to not in ("nan", "-"):
                    label = choice_key if choice_key and choice_key not in ("nan", "-", "Text") else None
                    nodes[qid]["choices"].append({"label": label, "next_id": go_to})
            else:
                if go_to and go_to != "nan":
                    label = choice_key if choice_key and choice_key != "nan" else "A"
                    nodes[qid]["choices"].append({"label": label, "next_id": go_to})
        else:
            if current_node and choice_key and choice_key != "nan" and go_to and go_to != "nan":
                nodes[current_node]["choices"].append({"label": choice_key, "next_id": go_to})

    # Determine root nodes: Q* nodes not referenced as Go to target by any other node
    referenced = set()
    for nid, node in nodes.items():
        for ch in node["choices"]:
            if ch["next_id"].startswith("Q"):
                referenced.add(ch["next_id"])
    root_nodes = [qid for qid in all_qids if qid not in referenced]

    return nodes, answers, root_nodes


def trace_paths(nodes: dict, answers: dict, root_nodes: list) -> list[dict]:
    all_paths = []

    def dfs(node_id: str, path: list, visited: frozenset):
        if node_id in visited:
            return
        visited = visited | {node_id}

        if node_id.startswith("ANS"):
            ans_text = answers.get(node_id, "")
            if ans_text:
                all_paths.append({"path": list(path), "answer_id": node_id,
                                   "answer_text": ans_text})
            return

        node = nodes.get(node_id)
        if not node or not node["choices"]:
            return

        for choice in node["choices"]:
            new_path = path + [{"node_id": node_id, "question": node["question"],
                                 "choice": choice["label"]}]
            dfs(choice["next_id"], new_path, visited)

    for root_id in root_nodes:
        dfs(root_id, [], frozenset())

    return all_paths


def build_document(path_data: dict) -> dict | None:
    ans_id = path_data["answer_id"]
    answer_text = path_data["answer_text"]
    path_nodes = path_data["path"]

    meta = ANSWER_META.get(ans_id)
    if not meta:
        return None  # skip if no metadata

    if path_nodes:
        # Root question = first node (what user actually asked about)
        root_q = path_nodes[0]["question"]
        root_qid = path_nodes[0]["node_id"]

        # Build conditions from branching choices
        conditions = []
        context_qs = []
        for step in path_nodes:
            if step["choice"]:
                conditions.append(f"{step['question']} → {step['choice']}")
                context_qs.append(f"{step['node_id']}: {step['question']} → {step['choice']}")
            else:
                context_qs.append(f"{step['node_id']}: {step['question']}")

        # Enriched question: root question + conditions
        if conditions:
            enriched_q = f"{root_q} เมื่อ{'; '.join(conditions)}?"
        else:
            enriched_q = f"{root_q}?"

        # Unique ID: root Q + ANS + short hash (ASCII-safe for AI Search key constraint)
        cond_slug = hashlib.md5(
            ("|".join(conditions)).encode("utf-8")
        ).hexdigest()[:8] if conditions else "direct"
        doc_id = f"{root_qid}_{ans_id}_{cond_slug}"
    else:
        enriched_q = ""
        conditions = []
        context_qs = []
        doc_id = ans_id

    return {
        "id": doc_id,
        "question": enriched_q,
        "answer": answer_text,
        "shortAnswer": meta["shortAnswer"],
        "category": meta["category"],
        "keywords": meta["keywords"],
        "conditions": conditions if conditions else [],
        "contextQuestions": context_qs,
        "sourceId": ans_id,
        "choiceType": "button" if conditions else "info",
    }


def main():
    parser = argparse.ArgumentParser(description="Flatten E-Expense Q&A → FAQ JSONL")
    parser.add_argument("--excel", default=DEFAULT_EXCEL)
    parser.add_argument("--output", default=OUTPUT_JSONL)
    parser.add_argument("--pretty", action="store_true", help="Output formatted JSON array")
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.exists():
        print(f"❌ Excel not found: {excel_path}")
        sys.exit(1)

    print(f"📖 Reading: {excel_path}")
    nodes, answers, root_nodes = parse_excel(str(excel_path))
    print(f"   {len(nodes)} question nodes, {len(answers)} answers, {len(root_nodes)} roots")

    print("🔀 Tracing all paths through decision tree...")
    paths = trace_paths(nodes, answers, root_nodes)
    print(f"   {len(paths)} raw paths found")

    print("📝 Building search documents...")
    docs = []
    seen_ids = set()
    for p in paths:
        doc = build_document(p)
        if doc and doc["id"] not in seen_ids:
            seen_ids.add(doc["id"])
            docs.append(doc)
    print(f"   {len(docs)} unique documents")

    # Category breakdown
    cats = defaultdict(int)
    for d in docs:
        cats[d["category"]] += 1
    print("\n📊 Categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")

    # Write
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.pretty:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            for doc in docs:
                json.dump(doc, f, ensure_ascii=False)
                f.write("\n")
    print(f"\n✅ Written: {output_path} ({len(docs)} documents)")

    # Sample
    print("\n📋 Sample (first 5):")
    for doc in docs[:5]:
        print(f"  [{doc['id']}]")
        print(f"  🏷️  {doc['category']}")
        print(f"  ❓ {doc['question'][:130]}")
        print(f"  💬 {doc['shortAnswer']}")
        if doc.get("conditions"):
            for c in doc["conditions"]:
                print(f"     ↳ {c}")
        print()


if __name__ == "__main__":
    main()
