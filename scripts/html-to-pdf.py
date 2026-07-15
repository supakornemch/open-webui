#!/usr/bin/env python3
"""Generate a professional PDF User Guide for Genie Enterprise Agent."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "genie-user-guide.pdf")

# ── Register Thai font ──
TTC_PATH = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/cf0dc8d3b09f9ba379660e591e82566e2b557949.asset/AssetData/Sarabun.ttc"
pdfmetrics.registerFont(TTFont("Sarabun", TTC_PATH, subfontIndex=0))
pdfmetrics.registerFont(TTFont("Sarabun-Bold", TTC_PATH, subfontIndex=1))

# ── Colors ──
C_PRIMARY = HexColor("#0071e3")
C_DARK = HexColor("#1d1d1f")
C_GRAY = HexColor("#6e6e73")
C_LIGHT_BG = HexColor("#f5f5f7")
C_BORDER = HexColor("#d2d2d7")
C_CODE_BG = HexColor("#1d1d1f")
C_WHITE = white

# ── Styles ──
# Thai needs larger leading (1.6-1.8x) due to ascending/descending marks
def make_styles():
    return {
        "title": ParagraphStyle(
            "Title", fontName="Sarabun-Bold", fontSize=24, leading=32,
            textColor=C_DARK, alignment=TA_CENTER, spaceAfter=4 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", fontName="Sarabun", fontSize=13, leading=22,
            textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=8 * mm,
        ),
        "h1": ParagraphStyle(
            "H1", fontName="Sarabun-Bold", fontSize=20, leading=30,
            textColor=C_PRIMARY, spaceBefore=12 * mm, spaceAfter=4 * mm,
        ),
        "h2": ParagraphStyle(
            "H2", fontName="Sarabun-Bold", fontSize=15, leading=24,
            textColor=C_DARK, spaceBefore=6 * mm, spaceAfter=3 * mm,
        ),
        "h3": ParagraphStyle(
            "H3", fontName="Sarabun-Bold", fontSize=13, leading=21,
            textColor=C_DARK, spaceBefore=4 * mm, spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body", fontName="Sarabun", fontSize=11, leading=20,
            textColor=C_DARK, alignment=TA_LEFT, spaceAfter=3 * mm,
        ),
        "bullet": ParagraphStyle(
            "Bullet", fontName="Sarabun", fontSize=11, leading=20,
            textColor=C_DARK, leftIndent=14, bulletIndent=0, spaceAfter=2.5 * mm,
        ),
        "code": ParagraphStyle(
            "Code", fontName="Sarabun", fontSize=10, leading=16,
            textColor=C_WHITE, backColor=C_CODE_BG,
            leftIndent=8, rightIndent=8, spaceBefore=2 * mm, spaceAfter=2 * mm,
            borderPadding=(8, 8, 8, 8),
        ),
        "badge": ParagraphStyle(
            "Badge", fontName="Sarabun-Bold", fontSize=10, leading=16,
            textColor=C_WHITE, backColor=C_PRIMARY,
            alignment=TA_CENTER, spaceAfter=2 * mm,
        ),
        "tip": ParagraphStyle(
            "Tip", fontName="Sarabun", fontSize=10, leading=18,
            textColor=C_GRAY, spaceAfter=3 * mm,
        ),
        "footer": ParagraphStyle(
            "Footer", fontName="Sarabun", fontSize=8, leading=12,
            textColor=C_GRAY, alignment=TA_CENTER,
        ),
    }


def add_screenshot(story, filename, styles, width=150 * mm):
    """Add a screenshot image to the story if it exists."""
    path = os.path.join(SCREENSHOTS_DIR, filename)
    if os.path.exists(path):
        try:
            img = Image(path, width=width, height=None)
            img.hAlign = "CENTER"
            # Calculate height maintaining aspect ratio
            from reportlab.lib.utils import ImageReader
            reader = ImageReader(path)
            iw, ih = reader.getSize()
            aspect = ih / iw
            img = Image(path, width=width, height=width * aspect)
            img.hAlign = "CENTER"
            story.append(Spacer(1, 2 * mm))
            story.append(img)
            story.append(Spacer(1, 2 * mm))
        except Exception as e:
            story.append(Paragraph(f"<i>[Image not available: {filename}]</i>", styles["tip"]))
    else:
        story.append(Paragraph(f"<i>[Screenshot not found: {filename}]</i>", styles["tip"]))


def add_hr(story):
    """Add a horizontal rule."""
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 2 * mm))


def make_table(data, col_widths=None):
    """Create a styled table."""
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_DARK),
        ("FONTNAME", (0, 0), (-1, 0), "Sarabun-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Sarabun"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEADING", (0, 0), (-1, -1), 18),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ])
    t.setStyle(style)
    return t


def build_cover_page(story, styles):
    """Build the cover page."""
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph("🪄 Genie", styles["title"]))
    story.append(Paragraph("Enterprise Knowledge User Guide", ParagraphStyle(
        "CoverSub", fontName="Sarabun-Bold", fontSize=18, leading=24,
        textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=4 * mm,
    )))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("คู่มือการใช้งาน Genie AI Assistant", styles["subtitle"]))
    story.append(Paragraph("สำหรับ Haadthip DIO Team", styles["subtitle"]))
    story.append(Spacer(1, 20 * mm))
    story.append(HRFlowable(width="40%", thickness=1, color=C_PRIMARY))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("เอกสารภายในองค์กร —  Confidential", styles["tip"]))
    story.append(PageBreak())


def build_toc(story, styles):
    """Build table of contents page."""
    story.append(Paragraph("สารบัญ", styles["h1"]))
    story.append(Spacer(1, 4 * mm))

    toc_items = [
        ("1", "📖 วิธีใช้ Genie — Open WebUI Wiki"),
        ("2", "📚 Knowledge Base"),
        ("3", "💬 Prompts"),
        ("4", "🤖 ขั้นตอนสร้าง Agent"),
        ("5", "🧠 Skills"),
        ("6", "🔧 ขั้นตอนเพิ่ม Tool (Advance)"),
    ]
    for num, title in toc_items:
        row = Table(
            [[Paragraph(f"<b>{num}</b>", styles["body"]),
              Paragraph(title, styles["h3"])]],
            colWidths=[12 * mm, None],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(row)

    story.append(PageBreak())


def build_section_guide(story, styles):
    """Section 1: วิธีใช้ Genie."""
    story.append(Paragraph("1. วิธีใช้ Genie — Open WebUI Wiki", styles["h1"]))
    story.append(Paragraph("คู่มือการใช้งาน Genie AI Assistant สำหรับพนักงานหาดทิพย์", styles["body"]))

    # แชทกับ Genie
    story.append(Paragraph("💬 แชทกับ Genie", styles["h2"]))
    for item in [
        "เปิด <b>New Chat</b> — เลือกโมเดลจาก dropdown ด้านบน",
        "พิมพ์คำถามเป็นภาษาไทยหรืออังกฤษก็ได้",
        "Genie ค้นหาจากฐานข้อมูลเอกสารภายในก่อนตอบ",
        "คำตอบจะอ้างอิงชื่อเอกสารต้นทาง",
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    # แนบไฟล์
    story.append(Paragraph("📎 แนบไฟล์ถาม", styles["h2"]))
    for item in [
        "ลากไฟล์ PDF, Excel, Word, CSV มาวางในแชท",
        "Genie อ่านเอกสารให้ แล้วถามรายละเอียดได้เลย",
        'ลอง: <font name="Sarabun">"สรุปเอกสารนี้ให้หน่อย"</font> หรือ <font name="Sarabun">"หาข้อมูลเกี่ยวกับ X ในไฟล์นี้"</font>',
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    # CSV example
    story.append(Paragraph("📊 ตัวอย่าง: CSV → HTML Preview", styles["h2"]))
    story.append(Paragraph(
        "อัปโหลดไฟล์ CSV ยอดขาย แล้วให้ Genie สร้าง HTML preview แบบ Bar Chart "
        "ให้ดูทันที — ไม่ต้องเขียนโค้ดเอง!", styles["body"]
    ))
    add_screenshot(story, "34-chat-with-csv.png", styles)
    story.append(Paragraph("<b>ผลลัพธ์</b> — Genie สร้าง Bar Chart ด้วย Chart.js ให้ดูในแชท:", styles["body"]))
    add_screenshot(story, "35-csv-html-preview.png", styles)

    # ฟีเจอร์พื้นฐาน
    story.append(Paragraph("🔍 ฟีเจอร์พื้นฐาน", styles["h2"]))

    features = [
        ("🎯 เลือกโมเดล", [
            "คลิกชื่อโมเดล → เลือกได้ตามต้องการ",
            "<b>Genie — Enterprise Knowledge</b> = AI องค์กร",
            "<b>MyAssistant</b> = GPT ทั่วไป",
        ]),
        ("📋 ประวัติแชท", [
            "ดูประวัติแชทที่ sidebar ด้านซ้าย",
            "กด Search เพื่อค้นหาแชทเก่า",
            "ตั้งชื่อแชทเพื่อจัดการง่ายขึ้น",
        ]),
        ("⚙️ ตั้งค่า", [
            "ปุ่ม Controls — ปรับอุณหภูมิ, System Prompt",
            "Available Tools — ดู Tools ที่เปิดใช้",
            "Voice Input — พิมพ์ด้วยเสียง",
        ]),
        ("🔗 แชร์แชท", [
            "แชร์ประวัติแชทให้เพื่อนร่วมทีม",
            "Export แชทเป็นไฟล์",
            "Import แชทจากไฟล์",
        ]),
    ]
    for title, items in features:
        story.append(Paragraph(f"<b>{title}</b>", styles["h3"]))
        for item in items:
            story.append(Paragraph(f"• {item}", styles["bullet"]))

    # Tips & Tricks
    story.append(Paragraph("🧠 Tips & Tricks", styles["h2"]))

    story.append(Paragraph("<b>✅ ควรถาม</b>", styles["h3"]))
    for q in ['"ตั้ง MFA ในมือถือยังไง"', '"สิทธิ์ลากี่วัน"', '"นโยบาย PDPA"', '"ต่อ VPN ไม่ได้ทำไง"', '"OT ได้เท่าไหร่"']:
        story.append(Paragraph(f"• {q}", styles["bullet"]))

    story.append(Paragraph("<b>❌ ไม่ควรถาม</b>", styles["h3"]))
    for q in ["ข้อมูลลับ/ความลับทางการค้า", "รหัสผ่าน หรือข้อมูลส่วนตัว", "ข้อมูลที่ไม่เกี่ยวกับองค์กร", "คำถามที่ไม่เป็นความจริง/เข้าใจผิด"]:
        story.append(Paragraph(f"• {q}", styles["bullet"]))

    # Use Cases
    story.append(Paragraph("🏢 Use Cases ตามแผนก (Enterprise AI)", styles["h2"]))
    story.append(Paragraph(
        "ตัวอย่างการประยุกต์ใช้ Genie สำหรับธุรกิจหาดทิพย์:", styles["body"]
    ))

    use_cases = [
        ("🛒 ฝ่ายขาย", ["<b>Sales Brief</b> — สรุปข้อมูลร้านค้าก่อนลงพื้นที่", "<b>Promotion Analyzer</b> — วิเคราะห์โปรโมชันที่ใช่"]),
        ("📢 การตลาด", ["<b>Local Content</b> — คอนเทนต์ภาษาใต้", "<b>Southern Campaign</b> — กิจกรรมออนกราวด์"]),
        ("🏭 ฝ่ายผลิต", ["<b>Demand Planner</b> — วางแผนผลิตตามดีมานด์", "<b>Maintenance Co-pilot</b> — ซ่อมบำรุงเครื่องจักร"]),
        ("🚚 ฝ่ายขนส่ง", ["<b>Route Optimizer</b> — เส้นทางประหยัดน้ำมัน", "<b>POD Agent</b> — ตรวจสอบใบส่งสินค้า"]),
        ("👥 ฝ่าย HR", ["<b>HR Benefits Bot</b> — สวัสดิการ 24 ชม.", "<b>Recruitment Agent</b> — กรองเรซูเม่"]),
        ("💻 ฝ่าย IT", ["<b>IT Helpdesk</b> — แก้ปัญหาไอทีเบื้องต้น", "<b>Cybersecurity Monitor</b> — ตรวจจับความผิดปกติ"]),
        ("💰 ฝ่ายการเงิน", ["<b>Expense Auditor</b> — ตรวจสอบใบเสร็จ", "<b>Credit Monitor</b> — ติดตามหนี้สินเชื่อ"]),
        ("🤝 ลูกค้าสัมพันธ์", ["<b>B2B Ordering Bot</b> — สั่งซื้อผ่าน Line", "<b>Cooler Service Agent</b> — แจ้งซ่อมตู้แช่"]),
    ]
    for dept, items in use_cases:
        story.append(Paragraph(f"<b>{dept}</b>", styles["h3"]))
        for item in items:
            story.append(Paragraph(f"• {item}", styles["bullet"]))

    story.append(Paragraph(
        '💡 ใช้ Prompts (<font name="Sarabun">/command</font>) สำหรับงานที่ต้องการคำสั่งเฉพาะ — Skills จะทำงานอัตโนมัติเมื่อเจอคำถามที่ตรง',
        styles["tip"]
    ))

    # Tools & Prompts วิธีใช้
    story.append(Paragraph("🛠️ วิธีใช้ Tools และ Prompts", styles["h2"]))
    tools_items = [
        "<b>Tools</b> — เปิด/ปิด Tool ได้ที่ Controls → Available Tools (เช่น Enterprise Search)",
        '<b>Prompts</b> — พิมพ์ <font name="Sarabun">/</font> ในแชท → เลือก Prompt ที่เซฟไว้ → ใช้ซ้ำได้ทันที',
        "<b>Knowledge</b> — ถ้าต้องการให้ Genie ใช้ Knowledge Base ให้เปิดใน Controls",
        "<b>Code Interpreter</b> — เปิดให้ Genie เขียนและรันโค้ด Python วิเคราะห์ข้อมูล",
        "<b>Web Search</b> — เปิดให้ Genie ค้นหาข้อมูลจาก internet",
    ]
    for item in tools_items:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    story.append(PageBreak())


def build_section_knowledge(story, styles):
    """Section 2: Knowledge Base."""
    story.append(Paragraph("2. Knowledge Base", styles["h1"]))
    story.append(Paragraph(
        "จัดการฐานความรู้ (Knowledge Base) สำหรับให้ Agent ใช้อ้างอิง", styles["body"]
    ))

    story.append(Paragraph("📖 Knowledge Base คืออะไร?", styles["h2"]))
    story.append(Paragraph(
        "Knowledge Base (KB) คือคลังเอกสารที่ Agent สามารถดึงมาอ่านเพื่อตอบคำถามได้ "
        "— เหมือนมีแฟ้มเอกสารไว้ให้ AI ค้นหา", styles["body"]
    ))
    for item in [
        "รองรับไฟล์: <b>PDF, DOCX, TXT, CSV, MD</b>",
        "สามารถอัปโหลดทีละไฟล์ หรือทั้งโฟลเดอร์",
        "เนื้อหาจะถูก chunk และ embed เป็น vector อัตโนมัติ",
        "เวลาถาม Agent จะค้นหาที่ KB ก่อน แล้วค่อยตอบ",
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    story.append(Paragraph("ขั้นตอนสร้าง Knowledge Base", styles["h2"]))
    story.append(Paragraph("<b>Step 1:</b> คลิก <b>Workspace</b> → <b>Knowledge</b> — จะเห็นรายการ Knowledge Bases ที่สร้างไว้", styles["body"]))
    add_screenshot(story, "32-knowledge-list.png", styles)

    story.append(Paragraph("<b>Step 2:</b> กด <b>New Knowledge</b> → ตั้งชื่อ (เช่น MFA Setup Guide) → เลือก <b>Public</b> → กด <b>Create Knowledge</b>", styles["body"]))
    add_screenshot(story, "33-knowledge-detail-mfa.png", styles)

    story.append(Paragraph("<b>Step 3:</b> อัปโหลดไฟล์ PDF/DOCX ลงใน Knowledge Base", styles["body"]))
    add_screenshot(story, "29-knowledge-with-mfa.png", styles)

    story.append(Paragraph("💡 แนะนำ", styles["h2"]))
    story.append(Paragraph("<b>✅ ใช้กับ Agent Enterprise</b>", styles["h3"]))
    for item in ["ประกาศ HR, ระเบียบ, คำสั่ง", "คู่มือ IT, นโยบายความปลอดภัย", "เอกสาร Open WebUI"]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))
    story.append(Paragraph("<b>⚠️ ข้อควรรู้</b>", styles["h3"]))
    for item in ["ขนาดไฟล์ไม่ควรเกิน 50MB", "ชื่อไฟล์ควรสื่อความหมาย (อังกฤษ)", "KB ที่อัปเดตแล้วต้องรอ re-index"]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    story.append(PageBreak())


def build_section_prompts(story, styles):
    """Section 3: Prompts."""
    story.append(Paragraph("3. Prompts", styles["h1"]))
    story.append(Paragraph("จัดการ Prompt Templates สำหรับเรียกใช้ซ้ำได้", styles["body"]))

    story.append(Paragraph("📝 Prompts คืออะไร?", styles["h2"]))
    story.append(Paragraph(
        "Prompts คือ <b>เทมเพลตคำสั่ง</b> ที่เซฟไว้ใช้กับ Agent ได้ทันที "
        "โดยไม่ต้องพิมพ์ซ้ำ — คล้ายๆ กับ shortcut คำสั่ง", styles["body"]
    ))

    # Example prompt
    story.append(Paragraph("ตัวอย่าง Prompt Template:", styles["h3"]))
    code_text = (
        '<font name="Sarabun" color="#34d399"># ตัวอย่าง Prompt Template</font><br/>'
        '<font name="Sarabun" color="#f59e0b">ชื่อ:</font> สรุปเอกสาร<br/>'
        '<font name="Sarabun" color="#f59e0b">Prompt:</font> ช่วยสรุปเอกสารต่อไปนี้เป็นภาษาไทย<br/>'
        '&nbsp;&nbsp;แบบ bullet points แยกเป็นหัวข้อ:<br/>'
        '&nbsp;&nbsp;1. ใจความสำคัญ<br/>'
        '&nbsp;&nbsp;2. รายละเอียด<br/>'
        '&nbsp;&nbsp;3. ข้อควรปฏิบัติ<br/>'
        '&nbsp;&nbsp;{content}'
    )
    story.append(Paragraph(code_text, styles["code"]))

    story.append(Paragraph("ขั้นตอนสร้าง Prompt", styles["h2"]))
    story.append(Paragraph("<b>Step 1:</b> คลิก <b>Workspace</b> → <b>Prompts</b>", styles["body"]))
    add_screenshot(story, "30-prompts-with-examples.png", styles)

    story.append(Paragraph("<b>Step 2:</b> กด <b>New Prompt</b> → กรอกข้อมูล:", styles["body"]))
    for item in [
        "<b>Prompt Name:</b> ตั้งชื่อที่จำง่าย (เช่น สรุปเอกสาร, ค้นหาเอกสาร)",
        '<b>Command:</b> พิมพ์ <font name="Sarabun">/summarize</font> หรือ <font name="Sarabun">/search</font> เพื่อใช้ในแชท',
        '<b>Prompt Content:</b> ข้อความคำสั่ง ใช้ <font name="Sarabun">{{variable}}</font> เป็นตัวแปร',
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    # Prompts table
    story.append(Paragraph("💬 ตัวอย่าง Prompt ที่สร้างไว้ — ทั้งหมด 14 รายการ (Public)", styles["h2"]))
    prompts_data = [
        ["ชื่อ", "คำสั่ง", "คำอธิบาย", "แผนก"],
        ["Sales Brief", "/sales-brief", "สรุปข้อมูลร้านค้าก่อนลงพื้นที่ขาย", "🛒 ขาย"],
        ["Promotion Analyzer", "/promo-analyze", "วิเคราะห์โปรโมชันเครื่องดื่ม", "📢 การตลาด"],
        ["Local Content Creator", "/local-content", "สร้างสื่อการตลาดภาษาใต้", "📢 การตลาด"],
        ["Production Demand Planner", "/production-plan", "วางแผนการผลิตตามดีมานด์", "🏭 ผลิต"],
        ["Machine Maintenance Guide", "/maintenance-guide", "ค้นหาวิธีซ่อมบำรุงเครื่องจักร", "🏭 ผลิต"],
        ["Route Optimizer", "/route-optimize", "วางเส้นทางจัดส่งประหยัดน้ำมัน", "🚚 ขนส่ง"],
        ["HR Benefits Assistant", "/hr-benefits", "ตอบคำถามสวัสดิการพนักงาน 24 ชม.", "👥 HR"],
        ["IT Helpdesk", "/it-helpdesk", "แก้ไขปัญหาไอทีเบื้องต้น", "💻 IT"],
        ["Expense Auditor", "/expense-check", "ตรวจสอบใบเสร็จตามนโยบาย", "💰 การเงิน"],
        ["Credit & Collection", "/credit-collect", "วิเคราะห์วงเงินสินเชื่อ", "💰 การเงิน"],
    ]
    story.append(make_table(prompts_data, col_widths=[45 * mm, 35 * mm, 70 * mm, 25 * mm]))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        '💡 พิมพ์ <font name="Sarabun">/</font> ในแชทแล้วเลือก Prompt ที่ต้องการใช้ '
        '— รองรับตัวแปร <font name="Sarabun">{{variable}}</font>',
        styles["tip"]
    ))

    story.append(PageBreak())


def build_section_agent(story, styles):
    """Section 4: Agent."""
    story.append(Paragraph("4. ขั้นตอนสร้าง Agent", styles["h1"]))
    story.append(Paragraph("สร้าง Model ที่มี Tool ติดตัว — พร้อมใช้งาน", styles["body"]))

    story.append(Paragraph("<b>Step 1:</b> Workspace → Models → เลือก Model", styles["h3"]))
    story.append(Paragraph(
        "คลิก <b>Workspace</b> → <b>Models</b> → เลือก model ที่ต้องการ "
        "(เช่น deploy-gpt-5.4-mini) หรือสร้างใหม่", styles["body"]
    ))
    add_screenshot(story, "12-create-model.png", styles)

    story.append(Paragraph("<b>Step 2:</b> เปิด Tools", styles["h3"]))
    story.append(Paragraph(
        "เลื่อนลงมาที่ส่วน <b>Tools</b> → ค้นหา → เลือก <b>Enterprise Search</b>", styles["body"]
    ))
    story.append(Paragraph(
        "เลือก <b>Native Mode (Agentic Mode)</b> — model จะเรียก Tool อัตโนมัติเวลาต้องการค้นหาเอกสาร",
        styles["body"]
    ))

    story.append(Paragraph("<b>Step 3:</b> Save", styles["h3"]))
    story.append(Paragraph(
        "กด <b>Save</b> → กลับมาดู Models list จะเห็น Model พร้อมใช้งาน", styles["body"]
    ))
    add_screenshot(story, "13-models-list.png", styles)

    story.append(PageBreak())


def build_section_skills(story, styles):
    """Section 5: Skills."""
    story.append(Paragraph("5. Skills", styles["h1"]))
    story.append(Paragraph(
        "จัดการ Skill set ให้ Agent — ความสามารถพิเศษนอกเหนือจาก Built-in", styles["body"]
    ))

    story.append(Paragraph("🧩 Skills คืออะไร?", styles["h2"]))
    story.append(Paragraph(
        "Skills คือ <b>ความสามารถเฉพาะทาง</b> ที่เพิ่มให้ Agent ได้ "
        "เช่น การคำนวณขั้นสูง, การดึงข้อมูลจาก API, การทำงานกับระบบเฉพาะ", styles["body"]
    ))
    for item in [
        "ต่างจาก Tools — Skills จะถูกเรียกใช้ <b>อัตโนมัติ</b> โดย Agent (ไม่ต้องเลือกเอง)",
        'เป็นเหมือน <font name="Sarabun">"พรสวรรค์"</font> ที่ Agent มีติดตัว',
        "สร้างด้วยภาษา Python เช่นเดียวกับ Tools",
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    story.append(Paragraph("<b>Step 1:</b> Workspace → Skills", styles["h3"]))
    add_screenshot(story, "31-skills-with-examples.png", styles)

    story.append(Paragraph("<b>Step 2:</b> สร้าง Skill", styles["h3"]))
    for item in [
        "<b>Skill Name:</b> ชื่อ Skill (เช่น Thai Date Converter)",
        "<b>Skill ID:</b> thai-date-converter",
        "<b>Description:</b> อธิบายว่า Skill นี้ทำอะไร",
        "<b>Instructions:</b> เขียนคำแนะนำในรูปแบบ Markdown",
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))

    # Skills table
    story.append(Paragraph("🧪 ตัวอย่าง Skills ที่สร้างไว้ — ทั้งหมด 13 รายการ (Public)", styles["h2"]))
    skills_data = [
        ["Skill", "คำอธิบาย", "แผนก"],
        ["Sales Pre-visit Agent", "สรุปข้อมูลร้านค้าก่อนลงพื้นที่ + Next-Best-Action", "🛒 ขาย"],
        ["Promotion Optimizer", "วิเคราะห์โปรโมชันและแนะนำรูปแบบที่เหมาะสม", "📢 การตลาด"],
        ["Southern Content Creator", "สร้างสื่อการตลาดภาษาใต้สำหรับเครื่องดื่ม", "📢 การตลาด"],
        ["Production Demand Planner", "คาดการณ์ปริมาณการผลิตตามดีมานด์", "🏭 ผลิต"],
        ["Maintenance Co-pilot", "ค้นหาคู่มือซ่อมบำรุงเครื่องจักร", "🏭 ผลิต"],
        ["Route Optimizer", "วางเส้นทางจัดส่งอัจฉริยะ", "🚚 ขนส่ง"],
        ["HR Benefits Bot", "ตอบคำถามสวัสดิการและสิทธิพนักงาน", "👥 HR"],
        ["IT Helpdesk Assistant", "ช่วยแก้ไขปัญหาไอทีเบื้องต้น", "💻 IT"],
        ["Expense Auditor", "ตรวจสอบใบเสร็จค่าใช้จ่ายตามนโยบาย", "💰 การเงิน"],
        ["Credit Monitor", "วิเคราะห์วงเงินสินเชื่อและติดตามหนี้", "💰 การเงิน"],
    ]
    story.append(make_table(skills_data, col_widths=[45 * mm, 85 * mm, 25 * mm]))

    story.append(Paragraph(
        "Skills จะถูกเรียกใช้โดย Agent อัตโนมัติเมื่อเจอคำถามที่ตรงกับความสามารถ — ไม่ต้องพิมพ์คำสั่งใด ๆ",
        styles["body"]
    ))

    # Tools vs Skills comparison
    story.append(Paragraph("📊 เปรียบเทียบ Tools vs Skills", styles["h2"]))
    compare_data = [
        ["คุณสมบัติ", "🔧 Tools", "🧠 Skills"],
        ["การเรียกใช้", "ต้องเลือกตอนถาม หรือให้ Agent เลือก", "เรียกอัตโนมัติ"],
        ["Class name", "class Tools:", "class Skills:"],
        ["เหมาะกับ", "ค้นหา, คำนวณ, API calls", "แปลงข้อมูล, จัดรูปแบบ, validate"],
        ["เปิด/ปิด", "เลือกเปิดเฉพาะ Model", "เพิ่มใน Model แล้วทำงานอัตโนมัติ"],
    ]
    story.append(make_table(compare_data, col_widths=[35 * mm, 65 * mm, 65 * mm]))

    story.append(Paragraph("💡 Use Case ตามแผนก", styles["h2"]))
    for dept, items in [
        ("🛒 ฝ่ายขาย", "รู้จักร้านค้าก่อนไปพบ, วิเคราะห์โปรโมชัน"),
        ("🏭 ฝ่ายผลิต", "วางแผนการผลิต, ซ่อมบำรุงเครื่องจักร"),
        ("🚚 ฝ่ายขนส่ง", "วางเส้นทาง, เพิ่มประสิทธิภาพน้ำมัน"),
        ("👥 ฝ่าย HR", "สวัสดิการ, สิทธิพนักงาน ตลอด 24 ชม."),
        ("💻 ฝ่าย IT", "Helpdesk อัตโนมัติ, Cybersecurity"),
        ("💰 ฝ่ายการเงิน", "ตรวจสอบค่าใช้จ่าย, ติดตามหนี้"),
        ("📢 ฝ่ายการตลาด", "คอนเทนต์ภาษาใต้, โปรโมชันเฉพาะพื้นที่"),
    ]:
        story.append(Paragraph(f"• <b>{dept}:</b> {items}", styles["bullet"]))

    story.append(PageBreak())


def build_section_tool(story, styles):
    """Section 6: Tool (Advance)."""
    story.append(Paragraph("6. ขั้นตอนเพิ่ม Tool (Advance)", styles["h1"]))
    story.append(Paragraph(
        "เพิ่ม Enterprise Search Tool สำหรับค้นหาเอกสารภายใน", styles["body"]
    ))

    story.append(Paragraph("<b>Step 1:</b> Workspace → Tools → New Tool", styles["h3"]))
    story.append(Paragraph(
        "คลิกเมนู <b>Workspace</b> → แท็บ <b>Tools</b> → กด <b>New Tool</b>", styles["body"]
    ))
    add_screenshot(story, "08-tools-page.png", styles)

    story.append(Paragraph("<b>Step 2:</b> กรอกข้อมูล", styles["h3"]))
    for item in [
        '<b>Tool Name:</b> <font name="Sarabun">Enterprise Search</font>',
        '<b>Tool ID:</b> <font name="Sarabun">enterprise_search</font>',
        '<b>Description:</b> <font name="Sarabun">Search internal docs, HR policies, and Open WebUI help via Azure AI Search.</font>',
    ]:
        story.append(Paragraph(f"• {item}", styles["bullet"]))
    add_screenshot(story, "09-create-tool.png", styles)

    story.append(Paragraph("<b>Step 3:</b> วางโค้ด Tool", styles["h3"]))
    story.append(Paragraph(
        "เปิดไฟล์ Tool → copy ทั้งหมด → วางใน Code Editor", styles["body"]
    ))
    add_screenshot(story, "06-tool-code-pasted.png", styles)

    story.append(Paragraph("<b>Step 4:</b> Save + Confirm", styles["h3"]))
    story.append(Paragraph(
        'กด <b>Save</b> → เช็ค <font name="Sarabun">"I acknowledge..."</font> → กด <b>Confirm</b>',
        styles["body"]
    ))
    add_screenshot(story, "07-confirm-dialog.png", styles)

    story.append(Paragraph("<b>Step 5:</b> ตรวจสอบ", styles["h3"]))
    story.append(Paragraph(
        "กลับมา Tools list จะเห็น <b>Enterprise Search</b> (Tools: 2)", styles["body"]
    ))
    add_screenshot(story, "10-tools-list-with-enterprise-search.png", styles)


def add_page_number(canvas_obj, doc):
    """Add page number footer to each page."""
    canvas_obj.saveState()
    page_num = doc.page
    # Footer
    canvas_obj.setFont("Sarabun", 8)
    canvas_obj.setFillColor(C_GRAY)
    canvas_obj.drawCentredString(A4[0] / 2, 15 * mm, f"Genie Enterprise Agent — User Guide  |  หน้า {page_num}")
    # Top line
    if page_num > 1:  # Skip cover page
        canvas_obj.setStrokeColor(C_BORDER)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
    canvas_obj.restoreState()


def main():
    styles = make_styles()

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=25 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="Genie Enterprise Agent — User Guide",
        author="Haadthip DIO Team",
        subject="คู่มือการใช้งาน Genie AI Assistant",
    )

    story = []

    # Cover page
    build_cover_page(story, styles)

    # Table of Contents
    build_toc(story, styles)

    # Sections
    build_section_guide(story, styles)
    build_section_knowledge(story, styles)
    build_section_prompts(story, styles)
    build_section_agent(story, styles)
    build_section_skills(story, styles)
    build_section_tool(story, styles)

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"✅ PDF generated: {OUTPUT_PATH}")
    print(f"   Size: {os.path.getsize(OUTPUT_PATH) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
