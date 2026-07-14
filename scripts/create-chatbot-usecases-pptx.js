/**
 * Generate "EnterpriseChat — AI Chatbot Use Cases" presentation.
 * 3 use cases:
 *   1) E-Expense Chatbot (MS Teams, RAG over FAQ KB)
 *   2) จัดซื้อ Bot (read master Excel, ตอบราคา, Python executor calculate)
 *   3) General Knowledge Ingestion (HR policy PDF, troubleshooting → Azure AI Search → tool)
 *
 * Palette: "Midnight Executive" — navy primary, gold accent, ice-blue secondary.
 * Fonts:   Georgia (headers) + Sarabun (body, Thai-capable).
 */

const pptxgen = require("pptxgenjs");

// ---- Palette (Midnight Executive + gold) -----------------------------------
const C = {
  navy:        "0E1F3F",   // dominant dark
  navyDeep:    "07142B",   // darker navy for title slides
  navyMid:     "1A335C",   // mid navy
  gold:        "D4A437",   // sharp accent
  goldSoft:    "E8C868",   // softer gold
  ice:         "DCE6F2",   // ice blue secondary
  iceSoft:     "EEF3FA",   // very light
  white:       "FFFFFF",
  ink:         "14233D",   // body text on light
  slate:       "5A6A82",   // muted body
  slateLight:  "8794A8",
  card:        "FFFFFF",
  cardLine:    "E2E8F2",
  green:       "1F8A5B",
  red:         "B23A48",
};

const F = { header: "Georgia", body: "Sarabun" };

// ---- helpers ---------------------------------------------------------------
const W = 13.333, H = 7.5; // LAYOUT_WIDE

function shadow(opt = {}) {
  return () => Object.assign(
    { type: "outer", color: "000000", blur: 8, offset: 3, angle: 90, opacity: 0.14 },
    opt
  );
}

// Simple flat icon (colored circle with a glyph text). Keeps deps at zero.
function iconBubble(slide, pres, { x, y, d = 0.7, fill = C.gold, glyph = "!", glyphColor = C.navyDeep, glyphSize = 24 }) {
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" },
    shadow: shadow({ blur: 6, offset: 2, opacity: 0.12 })(),
  });
  slide.addText(glyph, {
    x, y, w: d, h: d, align: "center", valign: "middle",
    fontFace: F.header, fontSize: glyphSize, bold: true, color: glyphColor, margin: 0,
  });
}

// Top bar (navy strip) with small kicker + page index. Light slide chrome.
function lightChrome(slide, pres, { kicker, pageIndex, totalPages, accent = C.gold }) {
  slide.background = { color: C.iceSoft };
  // left accent rail
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.16, h: H, fill: { color: accent }, line: { type: "none" },
  });
  // top thin rule
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.16, y: 0.55, w: W - 0.66, h: 0.012, fill: { color: C.cardLine }, line: { type: "none" },
  });
  // kicker (eyebrow)
  slide.addText(kicker.toUpperCase(), {
    x: 0.6, y: 0.22, w: 8, h: 0.3,
    fontFace: F.header, fontSize: 11, bold: true, color: C.slate,
    charSpacing: 4, margin: 0, valign: "middle",
  });
  // page index
  slide.addText(`${pageIndex} / ${totalPages}`, {
    x: W - 1.6, y: 0.22, w: 1.0, h: 0.3,
    fontFace: F.header, fontSize: 10, color: C.slateLight, align: "right", valign: "middle", margin: 0,
  });
}

function footer(slide, pres) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.16, y: H - 0.46, w: W - 0.66, h: 0.012, fill: { color: C.cardLine }, line: { type: "none" },
  });
  slide.addText("Haadthip · EnterpriseChat PoC", {
    x: 0.6, y: H - 0.42, w: 8, h: 0.3,
    fontFace: F.body, fontSize: 9, color: C.slateLight, valign: "middle", margin: 0,
  });
  slide.addText("Azure AI Search · AI Foundry · MS Teams", {
    x: W - 6.6, y: H - 0.42, w: 6.0, h: 0.3,
    fontFace: F.body, fontSize: 9, color: C.slateLight, align: "right", valign: "middle", margin: 0,
  });
}

// ---------------------------------------------------------------------------
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "EnterpriseChat — AI Chatbot Use Cases";
pres.author = "Haadthip · EnterpriseChat PoC";
const TOTAL = 10;

// ===========================================================================
// SLIDE 1 — Title
// ===========================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navyDeep };

  // large diagonal gold wedge bottom-right (motif)
  s.addShape(pres.shapes.RECTANGLE, {
    x: W - 4.2, y: H - 0.0, w: 5.5, h: 0.22,
    fill: { color: C.gold }, line: { type: "none" }, rotate: -8,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: W - 4.2, y: H - 0.35, w: 4.0, h: 0.08,
    fill: { color: C.goldSoft }, line: { type: "none" }, rotate: -8,
  });
  // small navy dots accent top-left
  for (let i = 0; i < 6; i++) {
    s.addShape(pres.shapes.OVAL, {
      x: 0.6 + i * 0.22, y: 0.6, w: 0.07, h: 0.07,
      fill: { color: i === 0 ? C.gold : C.navyMid }, line: { type: "none" },
    });
  }

  s.addText("HAADTHIP · ENTERPRISE CHAT", {
    x: 0.6, y: 2.0, w: 12, h: 0.4,
    fontFace: F.header, fontSize: 13, bold: true, color: C.goldSoft,
    charSpacing: 6, margin: 0,
  });

  s.addText("AI Chatbot Use Cases", {
    x: 0.6, y: 2.45, w: 12, h: 1.3,
    fontFace: F.header, fontSize: 60, bold: true, color: C.white, margin: 0,
  });

  s.addText("สามกรณีศึกษาที่นำ Generative AI มาใช้จริงในองค์กร", {
    x: 0.6, y: 3.85, w: 12, h: 0.6,
    fontFace: F.body, fontSize: 22, color: C.ice, margin: 0,
  });

  // three mini-pills of use case names
  const pills = [
    "1 · E-Expense FAQ",
    "2 · ผู้ช่วยจัดซื้อ",
    "3 · General Knowledge",
  ];
  pills.forEach((p, i) => {
    const x = 0.6 + i * 3.7;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.85, w: 3.45, h: 0.5,
      fill: { color: C.navyMid }, line: { color: C.gold, width: 0.75 },
    });
    s.addText(p, {
      x, y: 4.85, w: 3.45, h: 0.5, align: "center", valign: "middle",
      fontFace: F.body, fontSize: 13, bold: true, color: C.ice, margin: 0,
    });
  });

  s.addText("Sandbox PoC  ·  July 2026", {
    x: 0.6, y: 6.6, w: 8, h: 0.3,
    fontFace: F.header, fontSize: 12, color: C.slateLight, margin: 0,
  });
}

// ===========================================================================
// SLIDE 2 — Overview: 3 use cases at a glance
// ===========================================================================
{
  const s = pres.addSlide();
  lightChrome(s, pres, { kicker: "ภาพรวม", pageIndex: 2, totalPages: TOTAL });

  s.addText("สาม Use Cases ที่จะทำ", {
    x: 0.6, y: 0.75, w: 12, h: 0.6,
    fontFace: F.header, fontSize: 34, bold: true, color: C.navy, margin: 0,
  });
  s.addText("ทั้งสามกรณีใช้ Foundation เดียวกัน: Azure AI Search + LLM + Channel (Teams/Open WebUI)", {
    x: 0.6, y: 1.4, w: 12, h: 0.4,
    fontFace: F.body, fontSize: 15, color: C.slate, margin: 0,
  });

  const cards = [
    {
      n: "01", tag: "FAQ · RAG", accent: C.gold,
      title: "Chatbot E-Expense",
      desc: "อ่าน knowledge ที่ flatten จาก decision tree แล้วทำ RAG โดย user ถามผ่าน MS Teams",
      stack: ["MS Teams App", "AI Search (FAQ idx)", "GPT-5.4"],
    },
    {
      n: "02", tag: "Calc · Data", accent: C.green,
      title: "ผู้ช่วยจัดซื้อ",
      desc: "Bot อ่าน master Excel แล้วเทียบตอบราคา พร้อมเรียก Python Executor คำนวณราคาได้",
      stack: ["Excel Master", "Python Executor", "Tool-calling LLM"],
    },
    {
      n: "03", tag: "KB · Tool", accent: C.navyMid,
      title: "General Knowledge",
      desc: "Ingest HR policy PDF, troubleshooting guide เข้า Azure AI Search แล้วเขียน tool ไปเรียก",
      stack: ["Doc Intelligence", "AI Search KB", "Tool / Native Mode"],
    },
  ];

  const cw = 3.95, gap = 0.25, x0 = 0.6, y0 = 2.15, ch = 4.5;
  cards.forEach((c, i) => {
    const x = x0 + i * (cw + gap);
    // card
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: y0, w: cw, h: ch, fill: { color: C.card },
      line: { color: C.cardLine, width: 1 }, shadow: shadow()(),
    });
    // accent top bar
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: y0, w: cw, h: 0.14, fill: { color: c.accent }, line: { type: "none" },
    });
    // big number
    s.addText(c.n, {
      x: x + 0.35, y: y0 + 0.35, w: 2, h: 0.9,
      fontFace: F.header, fontSize: 44, bold: true, color: c.accent, margin: 0,
    });
    // tag pill
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + cw - 1.55, y: y0 + 0.5, w: 1.2, h: 0.32,
      fill: { color: C.iceSoft }, line: { color: c.accent, width: 0.75 },
    });
    s.addText(c.tag, {
      x: x + cw - 1.55, y: y0 + 0.5, w: 1.2, h: 0.32, align: "center", valign: "middle",
      fontFace: F.header, fontSize: 10, bold: true, color: c.accent, margin: 0,
    });
    // title
    s.addText(c.title, {
      x: x + 0.35, y: y0 + 1.4, w: cw - 0.7, h: 0.6,
      fontFace: F.header, fontSize: 22, bold: true, color: C.navy, margin: 0,
    });
    // divider
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.35, y: y0 + 2.05, w: 0.5, h: 0.03, fill: { color: c.accent }, line: { type: "none" },
    });
    // desc
    s.addText(c.desc, {
      x: x + 0.35, y: y0 + 2.2, w: cw - 0.7, h: 1.35,
      fontFace: F.body, fontSize: 13, color: C.ink, margin: 0, paraSpaceAfter: 4,
    });
    // stack chips
    c.stack.forEach((t, j) => {
      const cy = y0 + 3.55 + j * 0.3;
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.35, y: cy + 0.07, w: 0.08, h: 0.08, fill: { color: c.accent }, line: { type: "none" },
      });
      s.addText(t, {
        x: x + 0.52, y: cy, w: cw - 0.9, h: 0.28,
        fontFace: F.body, fontSize: 12, color: C.slate, margin: 0, valign: "middle",
      });
    });
  });

  footer(s, pres);
}

// ===========================================================================
// SLIDE 3 — Use Case 1: E-Expense — Section header + concept
// ===========================================================================
function sectionHeader(idx, title, subtitle, accent) {
  const s = pres.addSlide();
  s.background = { color: C.navy };
  // gold left column
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 4.4, h: H, fill: { color: accent }, line: { type: "none" },
  });
  // big ghost number
  s.addText(idx, {
    x: 0.2, y: 1.2, w: 4.0, h: 4.5,
    fontFace: F.header, fontSize: 300, bold: true, color: C.navyDeep, align: "center", valign: "middle", margin: 0,
  });
  // title block
  s.addText("USE CASE", {
    x: 5.0, y: 2.3, w: 7.5, h: 0.4,
    fontFace: F.header, fontSize: 14, bold: true, color: C.goldSoft, charSpacing: 6, margin: 0,
  });
  s.addText(title, {
    x: 5.0, y: 2.75, w: 7.6, h: 1.7,
    fontFace: F.header, fontSize: 46, bold: true, color: C.white, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.05, y: 4.55, w: 0.7, h: 0.05, fill: { color: C.gold }, line: { type: "none" },
  });
  s.addText(subtitle, {
    x: 5.0, y: 4.75, w: 7.4, h: 1.2,
    fontFace: F.body, fontSize: 18, color: C.ice, margin: 0,
  });
  return s;
}

sectionHeader("01", "Chatbot E-Expense",
  "ใส่ Knowledge ไว้แล้ว RAG เลย — user ถามผ่าน MS Teams app", C.gold);

// ===========================================================================
// SLIDE 4 — Use Case 1: architecture flow
// ===========================================================================
{
  const s = pres.addSlide();
  lightChrome(s, pres, { kicker: "Use Case 1 · E-Expense", pageIndex: 4, totalPages: TOTAL, accent: C.gold });

  s.addText("จาก Decision Tree → RAG บน MS Teams", {
    x: 0.6, y: 0.75, w: 12, h: 0.6,
    fontFace: F.header, fontSize: 30, bold: true, color: C.navy, margin: 0,
  });
  s.addText("นำ Q&A จาก Excel มา flatten เป็น FAQ docs → embed → hybrid search (BM25 + Vector + Semantic)", {
    x: 0.6, y: 1.4, w: 12, h: 0.4,
    fontFace: F.body, fontSize: 14, color: C.slate, margin: 0,
  });

  // 5-step flow boxes
  const steps = [
    { t: "Excel Q&A", d: "Decision tree\n(คำถาม + คำตอบ)", icon: "XLS", c: C.green },
    { t: "Flatten", d: "Trace paths →\n42 FAQ documents", icon: "↯", c: C.navyMid },
    { t: "Embed + Index", d: "text-embedding-3-large\n→ eexpense-faq-idx", icon: "≋", c: C.gold },
    { t: "Hybrid Search", d: "BM25 + Vector 3072d\n+ Semantic Ranker", icon: "⌕", c: C.navyMid },
    { t: "MS Teams", d: "User ถามผ่าน Teams\n→ คำตอบ + ที่มา", icon: "💬", c: C.green },
  ];
  const bw = 2.25, bgap = 0.18, bx0 = 0.6, by0 = 2.4, bh = 2.6;
  steps.forEach((st, i) => {
    const x = bx0 + i * (bw + bgap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: by0, w: bw, h: bh, fill: { color: C.card },
      line: { color: C.cardLine, width: 1 }, shadow: shadow()(),
    });
    // icon bubble
    iconBubble(s, pres, { x: x + bw / 2 - 0.4, y: by0 + 0.25, d: 0.8, fill: st.c, glyph: st.icon, glyphColor: C.white, glyphSize: 18 });
    s.addText(st.t, {
      x: x + 0.1, y: by0 + 1.15, w: bw - 0.2, h: 0.4,
      fontFace: F.header, fontSize: 16, bold: true, color: C.navy, align: "center", margin: 0,
    });
    s.addText(st.d, {
      x: x + 0.1, y: by0 + 1.6, w: bw - 0.2, h: 0.9,
      fontFace: F.body, fontSize: 11.5, color: C.slate, align: "center", margin: 0,
    });
    // arrow to next
    if (i < steps.length - 1) {
      s.addText("→", {
        x: x + bw - 0.05, y: by0 + bh / 2 - 0.2, w: 0.3, h: 0.4,
        fontFace: F.header, fontSize: 20, bold: true, color: C.gold, align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // key facts strip
  const facts = [
    { k: "42", v: "FAQ documents" },
    { k: "11", v: "หมวดหมู่" },
    { k: "3072d", v: "Vector embedding" },
    { k: "27", v: "Entry-point questions" },
  ];
  const fw = 2.9, fgap = 0.15, fx0 = 0.6, fy = 5.55;
  facts.forEach((f, i) => {
    const x = fx0 + i * (fw + fgap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: fy, w: fw, h: 0.95, fill: { color: C.navy }, line: { type: "none" },
    });
    s.addText(f.k, {
      x: x + 0.2, y: fy + 0.1, w: 1.2, h: 0.75,
      fontFace: F.header, fontSize: 28, bold: true, color: C.goldSoft, valign: "middle", margin: 0,
    });
    s.addText(f.v, {
      x: x + 1.1, y: fy + 0.1, w: fw - 1.2, h: 0.75,
      fontFace: F.body, fontSize: 13, color: C.ice, valign: "middle", margin: 0,
    });
  });

  footer(s, pres);
}

// ===========================================================================
// SLIDE 5 — Use Case 1: sample interaction + search strategy
// ===========================================================================
{
  const s = pres.addSlide();
  lightChrome(s, pres, { kicker: "Use Case 1 · E-Expense", pageIndex: 5, totalPages: TOTAL, accent: C.gold });

  s.addText("Search Strategy & ตัวอย่างการตอบ", {
    x: 0.6, y: 0.75, w: 12, h: 0.6,
    fontFace: F.header, fontSize: 30, bold: true, color: C.navy, margin: 0,
  });

  // Left: chat mockup (Teams-like)
  const lx = 0.6, ly = 1.6, lw = 6.3, lh = 5.0;
  s.addShape(pres.shapes.RECTANGLE, {
    x: lx, y: ly, w: lw, h: lh, fill: { color: C.white },
    line: { color: C.cardLine, width: 1 }, shadow: shadow()(),
  });
  // teams header bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: lx, y: ly, w: lw, h: 0.55, fill: { color: C.navy }, line: { type: "none" },
  });
  s.addText("●  E-Expense Bot   ·   Microsoft Teams", {
    x: lx + 0.2, y: ly, w: lw - 0.4, h: 0.55,
    fontFace: F.body, fontSize: 12, bold: true, color: C.white, valign: "middle", margin: 0,
  });

  // user bubble
  s.addShape(pres.shapes.RECTANGLE, {
    x: lx + 1.4, y: ly + 0.8, w: 4.6, h: 0.7, fill: { color: C.ice }, line: { type: "none" },
  });
  s.addText("ขอเบิกค่าอาหารล่วงหน้า 3 วัน มีทดรองจ่าย ต้องทำยังไง?", {
    x: lx + 1.55, y: ly + 0.8, w: 4.3, h: 0.7,
    fontFace: F.body, fontSize: 12, color: C.ink, valign: "middle", margin: 0,
  });
  s.addText("คุณ", {
    x: lx + 0.2, y: ly + 0.95, w: 1.1, h: 0.4,
    fontFace: F.body, fontSize: 11, bold: true, color: C.slate, valign: "middle", margin: 0,
  });

  // bot bubble
  s.addShape(pres.shapes.RECTANGLE, {
    x: lx + 0.2, y: ly + 1.75, w: 5.2, h: 2.95, fill: { color: C.iceSoft }, line: { color: C.gold, width: 0.75 },
  });
  s.addText("Bot", {
    x: lx + 0.35, y: ly + 1.85, w: 2, h: 0.3,
    fontFace: F.body, fontSize: 11, bold: true, color: C.gold, valign: "middle", margin: 0,
  });
  s.addText([
    { text: "เบิกล่วงหน้า 3 วัน + มีทดรองจ่าย → ", options: { fontSize: 12, color: C.ink } },
    { text: "กรอกแบบฟอร์ม PA-001", options: { fontSize: 12, bold: true, color: C.navy } },
    { text: " แนบใบเสร็จ พร้อมเอกสารการเดินทาง ส่งผู้อนุมัติลำดับที่ 1 (หัวหน้า)", options: { fontSize: 12, color: C.ink, breakLine: true } },
    { text: "\nหลักฐาน: ใบเสร็จ, แผนการเดินทาง, รายชื่อผู้ร่วมเดินทาง", options: { fontSize: 11.5, color: C.slate, breakLine: true } },
    { text: "\n📖 ที่มา: E-Expense FAQ · หมวด ค่าอาหาร/เบี้ยเลี้ยง", options: { fontSize: 10.5, italic: true, color: C.slateLight } },
  ], {
    x: lx + 0.35, y: ly + 2.15, w: 4.95, h: 2.45, fontFace: F.body, margin: 0, paraSpaceAfter: 4,
  });

  // quick-reply buttons
  ["📝 ดูขั้นตอนเพิ่ม", "📎 เปิดเอกสารต้นฉบับ", "❓ ถามต่อ"].forEach((b, i) => {
    const bx = lx + 0.2 + i * 1.75;
    s.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: ly + 4.35, w: 1.6, h: 0.42, fill: { color: C.white },
      line: { color: C.navyMid, width: 0.75 },
    });
    s.addText(b, {
      x: bx, y: ly + 4.35, w: 1.6, h: 0.42, align: "center", valign: "middle",
      fontFace: F.body, fontSize: 10, color: C.navy, margin: 0,
    });
  });

  // Right: search strategy ladder
  const rx = 7.2, ry = 1.6, rw = 5.55;
  s.addText("ลำดับการค้นหา", {
    x: rx, y: ry, w: rw, h: 0.4,
    fontFace: F.header, fontSize: 18, bold: true, color: C.navy, margin: 0,
  });
  const ladder = [
    { n: "1", t: "Quick Keyword Lookup", d: "ตรงกับ QUICK_MAP → ตอบทันที ไม่เรียก API" },
    { n: "2", t: "BM25 Full-Text (th.lucene)", d: "ค้นคำไทย ตัดคำ + scoring" },
    { n: "3", t: "Vector Search (cosine)", d: "text-embedding-3-large, 3072d" },
    { n: "4", t: "RRF Fusion → Semantic Ranker", d: "รวมผลแล้วจัดอันดับใหม่" },
    { n: "5", t: "State Machine → ตอบ", d: "1 ผล=ตอบตรง · หลายผล=ถามยืนยัน · 0=Fallback" },
  ];
  ladder.forEach((l, i) => {
    const yy = ry + 0.5 + i * 0.88;
    s.addShape(pres.shapes.RECTANGLE, {
      x: rx, y: yy, w: rw, h: 0.78, fill: { color: C.card },
      line: { color: C.cardLine, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: rx, y: yy, w: 0.6, h: 0.78, fill: { color: C.gold }, line: { type: "none" },
    });
    s.addText(l.n, {
      x: rx, y: yy, w: 0.6, h: 0.78, align: "center", valign: "middle",
      fontFace: F.header, fontSize: 20, bold: true, color: C.navyDeep, margin: 0,
    });
    s.addText(l.t, {
      x: rx + 0.75, y: yy + 0.07, w: rw - 0.9, h: 0.35,
      fontFace: F.body, fontSize: 13, bold: true, color: C.navy, margin: 0,
    });
    s.addText(l.d, {
      x: rx + 0.75, y: yy + 0.4, w: rw - 0.9, h: 0.32,
      fontFace: F.body, fontSize: 11, color: C.slate, margin: 0,
    });
  });

  footer(s, pres);
}

// ===========================================================================
// SLIDE 6 — Use Case 2: ผู้ช่วยจัดซื้อ — Section header
// ===========================================================================
sectionHeader("02", "ผู้ช่วยจัดซื้อ",
  "Bot อ่าน master Excel แล้วเทียบตอบราคา — เรียก Python Executor คำนวณได้", C.green);

// ===========================================================================
// SLIDE 7 — Use Case 2: architecture + sample
// ===========================================================================
{
  const s = pres.addSlide();
  lightChrome(s, pres, { kicker: "Use Case 2 · จัดซื้อ", pageIndex: 7, totalPages: TOTAL, accent: C.green });

  s.addText("อ่าน Master Excel → เทียบราคา → คำนวณด้วย Python", {
    x: 0.6, y: 0.75, w: 12, h: 0.6,
    fontFace: F.header, fontSize: 28, bold: true, color: C.navy, margin: 0,
  });
  s.addText("Tool-calling LLM: model ตัดสินใจเองว่าจะค้นราคา / คำนวณ / สรุป", {
    x: 0.6, y: 1.35, w: 12, h: 0.4,
    fontFace: F.body, fontSize: 14, color: C.slate, margin: 0,
  });

  // Left: architecture
  const lx = 0.6, ly = 1.95, lw = 6.2;
  s.addText("Architecture", {
    x: lx, y: ly, w: lw, h: 0.35,
    fontFace: F.header, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });
  const arch = [
    { t: "User (Teams / Open WebUI)", d: "“ราคาท่อ PVC 2 นิ้ว 50 เส้น รวม VAT?”", c: C.green, glyph: "👤" },
    { t: "LLM (Tool-calling / Native Mode)", d: "วางแผน → เลือก tool → รวมผล → ตอบ", c: C.navyMid, glyph: "✦" },
    { t: "Tool: read_master_excel()", d: "อ่าน master price list (.xlsx) → filter/sort", c: C.gold, glyph: "▤" },
    { t: "Tool: python_calculate()", d: "Python Executor: คำนวณราคา, ส่วนลด, VAT, ยอดรวม", c: C.gold, glyph: "Σ" },
    { t: "ตอบกลับ user", d: "ราคา/หน่วย + บวกลบยอด + แหล่งอ้างอิง row", c: C.green, glyph: "✓" },
  ];
  arch.forEach((a, i) => {
    const yy = ly + 0.45 + i * 0.85;
    s.addShape(pres.shapes.RECTANGLE, {
      x: lx, y: yy, w: lw, h: 0.72, fill: { color: C.card },
      line: { color: C.cardLine, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: lx, y: yy, w: 0.1, h: 0.72, fill: { color: a.c }, line: { type: "none" },
    });
    iconBubble(s, pres, { x: lx + 0.22, y: yy + 0.11, d: 0.5, fill: a.c, glyph: a.glyph, glyphColor: C.white, glyphSize: 16 });
    s.addText(a.t, {
      x: lx + 0.85, y: yy + 0.06, w: lw - 1.0, h: 0.32,
      fontFace: F.body, fontSize: 13, bold: true, color: C.navy, margin: 0,
    });
    s.addText(a.d, {
      x: lx + 0.85, y: yy + 0.36, w: lw - 1.0, h: 0.3,
      fontFace: F.body, fontSize: 11, color: C.slate, margin: 0,
    });
    if (i < arch.length - 1) {
      s.addText("↓", {
        x: lx + 0.22, y: yy + 0.66, w: 0.5, h: 0.22,
        fontFace: F.header, fontSize: 14, bold: true, color: C.gold, align: "center", margin: 0,
      });
    }
  });

  // Right: sample master excel table + answer
  const rx = 7.05, ry = 1.95, rw = 5.7;
  s.addText("Master Price List (ตัวอย่าง)", {
    x: rx, y: ry, w: rw, h: 0.35,
    fontFace: F.header, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });
  const head = [
    { text: "รหัส", options: { fill: { color: C.navy }, color: C.white, bold: true, align: "left", valign: "middle" } },
    { text: "รายการ", options: { fill: { color: C.navy }, color: C.white, bold: true, align: "left", valign: "middle" } },
    { text: "หน่วย", options: { fill: { color: C.navy }, color: C.white, bold: true, align: "center", valign: "middle" } },
    { text: "ราคา/หน่วย", options: { fill: { color: C.navy }, color: C.white, bold: true, align: "right", valign: "middle" } },
  ];
  const rows = [
    ["PVC-020", "ท่อ PVC 2\"", "เส้น", "45.00"],
    ["PVC-025", "ท่อ PVC 2.5\"", "เส้น", "68.00"],
    ["ELB-020", "ข้อศอก 90° 2\"", "ตัว", "12.50"],
  ];
  const tableRows = [head];
  rows.forEach((r, i) => {
    const hl = i === 0; // highlight matched row
    tableRows.push(r.map((cell, j) => ({
      text: cell,
      options: {
        fill: { color: hl ? "FFF4D6" : (i % 2 ? C.iceSoft : C.white) },
        color: C.ink, bold: hl,
        align: j === 2 ? "center" : (j === 3 ? "right" : "left"),
        valign: "middle",
      },
    })));
  });
  s.addTable(tableRows, {
    x: rx, y: ry + 0.4, w: rw, colW: [1.25, 2.15, 0.95, 1.35],
    rowH: 0.42, fontFace: F.body, fontSize: 12, border: { pt: 0.5, color: C.cardLine },
  });

  // answer callout
  s.addShape(pres.shapes.RECTANGLE, {
    x: rx, y: ry + 2.0, w: rw, h: 2.1, fill: { color: C.navy }, line: { type: "none" },
  });
  s.addText("คำตอบจาก Bot", {
    x: rx + 0.2, y: ry + 2.1, w: rw - 0.4, h: 0.32,
    fontFace: F.header, fontSize: 12, bold: true, color: C.goldSoft, charSpacing: 3, margin: 0,
  });
  s.addText([
    { text: "ท่อ PVC 2\" × 50 เส้น", options: { fontSize: 13, color: C.ice, breakLine: true } },
    { text: "45.00 × 50 = ", options: { fontSize: 13, color: C.ice } },
    { text: "2,250.00 บาท", options: { fontSize: 14, bold: true, color: C.goldSoft, breakLine: true } },
    { text: "+ VAT 7% = ", options: { fontSize: 12, color: C.ice } },
    { text: "2,407.50 บาท", options: { fontSize: 14, bold: true, color: C.goldSoft, breakLine: true } },
    { text: " calc โดย python_calculate() · master: PVC-020", options: { fontSize: 10, italic: true, color: C.slateLight } },
  ], {
    x: rx + 0.2, y: ry + 2.45, w: rw - 0.4, h: 1.55, fontFace: F.body, margin: 0, paraSpaceAfter: 3,
  });

  footer(s, pres);
}

// ===========================================================================
// SLIDE 8 — Use Case 3: General Knowledge — Section header
// ===========================================================================
sectionHeader("03", "General Knowledge",
  "Ingest HR policy / troubleshooting เข้า Azure AI Search แล้วเขียน tool ไปเรียก", C.navyMid);

// ===========================================================================
// SLIDE 9 — Use Case 3: pipeline + tool integration
// ===========================================================================
{
  const s = pres.addSlide();
  lightChrome(s, pres, { kicker: "Use Case 3 · General Knowledge", pageIndex: 9, totalPages: TOTAL, accent: C.navyMid });

  s.addText("Ingest → Index → Tool calling", {
    x: 0.6, y: 0.75, w: 12, h: 0.6,
    fontFace: F.header, fontSize: 30, bold: true, color: C.navy, margin: 0,
  });
  s.addText("ใช้ Azure AI Document Intelligence extract → AI Search index → Open WebUI Tool (Native Mode)", {
    x: 0.6, y: 1.35, w: 12, h: 0.4,
    fontFace: F.body, fontSize: 14, color: C.slate, margin: 0,
  });

  // Left: ingestion pipeline (vertical)
  const lx = 0.6, ly = 2.0, lw = 5.6;
  s.addText("Ingestion Pipeline", {
    x: lx, y: ly, w: lw, h: 0.35,
    fontFace: F.header, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });
  const pipe = [
    { t: "Source files", d: "HR policy PDF, MiHCM manual, IT troubleshooting", c: C.green, glyph: "📄" },
    { t: "Document Intelligence (Layout)", d: "extract text + ตารางเป็น markdown, แยกหัวข้อ/รูป", c: C.navyMid, glyph: "🔍" },
    { t: "Chunk + Classify", d: "แบ่ง chunk · tag category (HR, IT, policy)", c: C.navyMid, glyph: "✂" },
    { t: "Embed + Upload", d: "text-embedding-3-large → AI Search index", c: C.gold, glyph: "≋" },
    { t: "Knowledge Source + KB", d: "searchIndex KS · เพิ่มเข้า haadthip-kb", c: C.gold, glyph: "📚" },
  ];
  pipe.forEach((p, i) => {
    const yy = ly + 0.45 + i * 0.82;
    s.addShape(pres.shapes.RECTANGLE, {
      x: lx, y: yy, w: lw, h: 0.7, fill: { color: C.card },
      line: { color: C.cardLine, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: lx, y: yy, w: 0.1, h: 0.7, fill: { color: p.c }, line: { type: "none" },
    });
    iconBubble(s, pres, { x: lx + 0.22, y: yy + 0.1, d: 0.5, fill: p.c, glyph: p.glyph, glyphColor: C.white, glyphSize: 16 });
    s.addText(p.t, {
      x: lx + 0.85, y: yy + 0.06, w: lw - 1.0, h: 0.3,
      fontFace: F.body, fontSize: 13, bold: true, color: C.navy, margin: 0,
    });
    s.addText(p.d, {
      x: lx + 0.85, y: yy + 0.35, w: lw - 1.0, h: 0.3,
      fontFace: F.body, fontSize: 11, color: C.slate, margin: 0,
    });
    if (i < pipe.length - 1) {
      s.addText("↓", {
        x: lx + 0.22, y: yy + 0.64, w: 0.5, h: 0.2,
        fontFace: F.header, fontSize: 14, bold: true, color: C.gold, align: "center", margin: 0,
      });
    }
  });

  // Right: tool integration + example
  const rx = 6.55, ry = 2.0, rw = 6.2;
  s.addText("Tool Calling (Open WebUI Native Mode)", {
    x: rx, y: ry, w: rw, h: 0.35,
    fontFace: F.header, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });

  // mini architecture (boxes)
  s.addShape(pres.shapes.RECTANGLE, {
    x: rx, y: ry + 0.45, w: rw, h: 1.4, fill: { color: C.iceSoft },
    line: { color: C.cardLine, width: 1 },
  });
  const boxY = ry + 0.6, boxH = 1.1;
  const tboxes = [
    { t: "User", d: "“ลากิจ 3 วัน ต้องทำอะไรบ้าง?”" },
    { t: "LLM", d: "deploy-gpt-5.4-mini\n(think → call tool)" },
    { t: "Tool", d: "search_knowledge()\n→ AI Search KB" },
  ];
  tboxes.forEach((b, i) => {
    const bw = 1.85;
    const bx = rx + 0.2 + i * (bw + 0.1);
    s.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: boxY, w: bw, h: boxH, fill: { color: C.white },
      line: { color: C.navyMid, width: 1 },
    });
    s.addText(b.t, {
      x: bx, y: boxY + 0.08, w: bw, h: 0.3,
      fontFace: F.header, fontSize: 12, bold: true, color: C.navy, align: "center", margin: 0,
    });
    s.addText(b.d, {
      x: bx + 0.1, y: boxY + 0.38, w: bw - 0.2, h: 0.65,
      fontFace: F.body, fontSize: 10.5, color: C.slate, align: "center", margin: 0,
    });
    if (i < tboxes.length - 1) {
      s.addText("→", {
        x: bx + bw - 0.05, y: boxY + boxH / 2 - 0.15, w: 0.2, h: 0.3,
        fontFace: F.header, fontSize: 16, bold: true, color: C.gold, align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // tool code snippet (compact)
  s.addShape(pres.shapes.RECTANGLE, {
    x: rx, y: ry + 2.0, w: rw, h: 2.05, fill: { color: C.navyDeep }, line: { type: "none" },
  });
  s.addText("Python tool (≈40 บรรทัด)", {
    x: rx + 0.2, y: ry + 2.1, w: rw - 0.4, h: 0.3,
    fontFace: F.header, fontSize: 11, bold: true, color: C.goldSoft, charSpacing: 3, margin: 0,
  });
  s.addText([
    { text: "class Tools:", options: { color: C.ice, breakLine: true } },
    { text: "  async def ", options: { color: C.ice } },
    { text: "search_knowledge", options: { color: C.goldSoft, bold: true } },
    { text: "(self, query: str) -> str:", options: { color: C.ice, breakLine: true } },
    { text: '    """ค้น HR / IT policy / troubleshooting"""', options: { color: C.slateLight, italic: true, breakLine: true } },
    { text: "    ks = [{knowledgeSourceName,", options: { color: C.ice, breakLine: true } },
    { text: "          kind:'searchIndex'}]", options: { color: C.ice, breakLine: true } },
    { text: "    → POST knowledgebases(", options: { color: C.ice } },
    { text: "'haadthip-kb'", options: { color: C.goldSoft } },
    { text: ")", options: { color: C.ice, breakLine: true } },
    { text: "    return top_k docs → model สรุป + อ้างอิง", options: { color: C.ice } },
  ], {
    x: rx + 0.25, y: ry + 2.4, w: rw - 0.45, h: 1.6,
    fontFace: "Consolas", fontSize: 12, margin: 0, paraSpaceAfter: 2,
  });

  // why tool > pipe row
  s.addShape(pres.shapes.RECTANGLE, {
    x: rx, y: ry + 4.2, w: rw, h: 0.78, fill: { color: C.card },
    line: { color: C.gold, width: 0.75 },
  });
  s.addText("ทำไมใช้ Tool ไม่ใช่ Pipe", {
    x: rx + 0.2, y: ry + 4.28, w: rw - 0.4, h: 0.28,
    fontFace: F.header, fontSize: 11, bold: true, color: C.navy, charSpacing: 2, margin: 0,
  });
  s.addText("model เลือก tool เอง · ใช้หลาย tool พร้อมกันได้ (KB + web search) · เปลี่ยน model จาก UI · โค้ดน้อยกว่า ~10×", {
    x: rx + 0.2, y: ry + 4.55, w: rw - 0.4, h: 0.4,
    fontFace: F.body, fontSize: 11.5, color: C.ink, margin: 0,
  });

  footer(s, pres);
}

// ===========================================================================
// SLIDE 10 — Summary + shared foundation
// ===========================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navyDeep };

  // top gold rule
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 0.6, w: 0.7, h: 0.05, fill: { color: C.gold }, line: { type: "none" },
  });
  s.addText("สรุป", {
    x: 0.6, y: 0.75, w: 12, h: 0.7,
    fontFace: F.header, fontSize: 40, bold: true, color: C.white, margin: 0,
  });
  s.addText("สาม use cases ใช้ Foundation เดียวกัน — ต่างกันที่ data source, channel และ tool", {
    x: 0.6, y: 1.5, w: 12, h: 0.5,
    fontFace: F.body, fontSize: 17, color: C.ice, margin: 0,
  });

  // 3 columns recap
  const rec = [
    { n: "01", t: "E-Expense FAQ", pts: ["MS Teams channel", "FAQ hybrid search", "42 docs · 11 หมวด"], c: C.gold },
    { n: "02", t: "ผู้ช่วยจัดซื้อ", pts: ["อ่าน master Excel", "Python Executor คำนวณ", "Tool-calling LLM"], c: C.green },
    { n: "03", t: "General Knowledge", pts: ["Doc Intelligence ingest", "AI Search KB", "Tool / Native Mode"], c: C.ice },
  ];
  const cw = 3.95, gap = 0.25, x0 = 0.6, y0 = 2.25, ch = 2.85;
  rec.forEach((c, i) => {
    const x = x0 + i * (cw + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: y0, w: cw, h: ch, fill: { color: C.navy }, line: { color: c.c, width: 0.75 },
    });
    s.addText(c.n, {
      x: x + 0.3, y: y0 + 0.2, w: 2, h: 0.6,
      fontFace: F.header, fontSize: 30, bold: true, color: c.c, margin: 0,
    });
    s.addText(c.t, {
      x: x + 0.3, y: y0 + 0.85, w: cw - 0.6, h: 0.4,
      fontFace: F.header, fontSize: 18, bold: true, color: C.white, margin: 0,
    });
    c.pts.forEach((p, j) => {
      s.addText("·  " + p, {
        x: x + 0.3, y: y0 + 1.4 + j * 0.4, w: cw - 0.6, h: 0.35,
        fontFace: F.body, fontSize: 13, color: C.ice, margin: 0,
      });
    });
  });

  // shared foundation bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 5.45, w: 12.13, h: 1.35, fill: { color: C.navyMid }, line: { color: C.gold, width: 0.75 },
  });
  s.addText("SHARED FOUNDATION", {
    x: 0.85, y: 5.55, w: 8, h: 0.3,
    fontFace: F.header, fontSize: 11, bold: true, color: C.goldSoft, charSpacing: 4, margin: 0,
  });
  const found = ["Azure AI Search", "Azure AI Foundry (GPT-5.4)", "LiteLLM proxy", "Open WebUI / MS Teams", "Managed Identity"];
  found.forEach((f, i) => {
    const bx = 0.85 + i * 2.36;
    s.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: 5.95, w: 2.2, h: 0.55, fill: { color: C.navyDeep }, line: { color: C.ice, width: 0.5 },
    });
    s.addText(f, {
      x: bx, y: 5.95, w: 2.2, h: 0.55, align: "center", valign: "middle",
      fontFace: F.body, fontSize: 11, color: C.ice, margin: 0,
    });
  });

  s.addText("Next: เริ่มจาก E-Expense (knowledge พร้อม) → จัดซื้อ (Excel + Python) → General KB ingest", {
    x: 0.6, y: 7.0, w: 12, h: 0.35,
    fontFace: F.body, fontSize: 13, italic: true, color: C.goldSoft, margin: 0,
  });
}

// ===========================================================================
pres.writeFile({ fileName: "/Users/supakorn.emch/Workspace/Haadthip/EnterpriseChat/EnterpriseChat-Chatbot-UseCases.pptx" })
  .then((fn) => console.log("WROTE:", fn));
