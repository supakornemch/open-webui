const pptxgen = require("pptxgenjs");
const path = require("path");

const SCREENSHOTS = path.resolve(__dirname, "..", "screenshots");
const OUT = path.resolve(__dirname, "..", "EnterpriseChat-Walkthrough-2026-07-09.pptx");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "EnterpriseChat Team";
pres.title = "EnterpriseChat (Genie) — User Walkthrough";

const C = {
  bg:      "0D1117",
  surface: "161B22",
  border:  "30363D",
  text:    "C9D1D9",
  dim:     "8B949E",
  blue:    "58A6FF",
  green:   "3FB950",
  purple:  "BC8CFF",
  orange:  "D29922",
  teal:    "39D2C0",
  red:     "F85149",
  white:   "F0F6FC",
};

const makeShadow = () => ({ type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.2 });

// ============================================================
// Slide 1: Title
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 1.6, w: 0.06, h: 1.8, fill: { color: C.teal } });
  s.addText("EnterpriseChat", { x: 1.1, y: 1.5, w: 7, h: 0.8, fontSize: 44, fontFace: "Arial Black", color: C.white, bold: true, margin: 0 });
  s.addText('"Genie" — Your AI Assistant', { x: 1.1, y: 2.3, w: 7, h: 0.6, fontSize: 28, fontFace: "Arial", color: C.teal, margin: 0 });
  s.addText("genie.haadthip.com · Azure Sandbox POC · RG-ENTCHAT-POC-SAND-SEA", { x: 1.1, y: 3.2, w: 7, h: 0.4, fontSize: 13, fontFace: "Arial", color: C.dim, margin: 0 });
  s.addText("9 July 2026", { x: 1.1, y: 3.7, w: 4, h: 0.4, fontSize: 12, fontFace: "Arial", color: C.dim, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.1, w: 10, h: 0.525, fill: { color: C.surface } });
}

// ============================================================
// Slide 2: Agenda
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Agenda", { x: 0.7, y: 0.4, w: 8, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });

  const items = [
    ["01", "What is Genie?", "Architecture, key numbers, how it works"],
    ["02", "Getting Started", "Login, interface tour, basic chat"],
    ["03", "Knowledge Bases", "4 KBs — search corporate docs, SAP, IR, HR"],
    ["04", "Tools & Functions", "E-Expense FAQ, web search, custom tools"],
    ["05", "Model Selection & Prompts", "Which model when, custom system prompts"],
    ["06", "LiteLLM Dashboard", "Token tracking, cost, API keys, audit logs"],
    ["07", "Resources & Community", "Pre-built tools, functions, prompts from GitHub"],
    ["08", "Integration & Next Steps", "Dev tools, API access, feedback"],
  ];

  items.forEach(([num, title, desc], i) => {
    const y = 1.4 + i * 0.57;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: y, w: 0.06, h: 0.45, fill: { color: C.teal } });
    s.addText(num, { x: 1.0, y: y, w: 0.5, h: 0.45, fontSize: 18, fontFace: "Arial Black", color: C.teal, valign: "middle", margin: 0 });
    s.addText(title, { x: 1.6, y: y, w: 3, h: 0.25, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, valign: "middle", margin: 0 });
    s.addText(desc, { x: 1.6, y: y + 0.22, w: 5, h: 0.2, fontSize: 10, fontFace: "Arial", color: C.dim, valign: "top", margin: 0 });
  });
}

// ============================================================
// Slide 3: Architecture
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("What is Genie?", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
  s.addText("Enterprise AI Chat — built on Open WebUI + LiteLLM + Azure AI Foundry", { x: 0.7, y: 0.8, w: 8, h: 0.3, fontSize: 12, fontFace: "Arial", color: C.dim, margin: 0 });

  s.addImage({ path: path.join(SCREENSHOTS, "architecture.png"), x: 0.5, y: 1.2, w: 9, h: 3.5, sizing: { type: "contain", w: 9, h: 3.5 } });

  s.addText("genie.haadthip.com → Open WebUI → LiteLLM Proxy → Azure AI Foundry (GPT-5.4)", { x: 0.7, y: 4.85, w: 8.5, h: 0.25, fontSize: 10, fontFace: "Arial", color: C.teal, italic: true, margin: 0 });
  s.addText("Entra ID SSO (login with @haadthip.com) · 5 AI Models · 4 Knowledge Bases · Token Tracking", { x: 0.7, y: 5.1, w: 8.5, h: 0.25, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
}

// ============================================================
// Slide 4: Getting Started
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Getting Started", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });

  s.addImage({ path: path.join(SCREENSHOTS, "openwebui.png"), x: 0.4, y: 1.0, w: 5.0, h: 3.8, sizing: { type: "contain", w: 5.0, h: 3.8 } });

  const steps = [
    ["1", "Go to genie.haadthip.com", "Open any browser"],
    ["2", "Sign in with Microsoft", "Use your @haadthip.com account"],
    ["3", "New Chat", "Click \"New Chat\" or just start typing"],
    ["4", "Select Model", "Dropdown top-left — pick GPT-5.4 model"],
    ["5", "Ask anything!", "English or Thai — chat naturally"],
  ];

  const startX = 5.7;
  steps.forEach(([num, title, desc], i) => {
    const y = 1.0 + i * 0.78;
    s.addShape(pres.shapes.RECTANGLE, { x: startX, y, w: 3.6, h: 0.62, fill: { color: C.surface }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: startX, y, w: 0.05, h: 0.62, fill: { color: C.blue } });
    s.addText(num, { x: startX + 0.15, y: y + 0.1, w: 0.3, h: 0.4, fontSize: 18, fontFace: "Arial Black", color: C.blue, margin: 0 });
    s.addText(title, { x: startX + 0.5, y: y + 0.08, w: 2.8, h: 0.25, fontSize: 12, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
    s.addText(desc, { x: startX + 0.5, y: y + 0.34, w: 2.8, h: 0.2, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
  });

  s.addText("genie.haadthip.com", { x: 0.7, y: 5.0, w: 5, h: 0.3, fontSize: 11, fontFace: "Consolas", color: C.blue, margin: 0 });
}

// ============================================================
// Slide 5: Knowledge Bases
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Knowledge Bases", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
  s.addText("4 Knowledge Bases — search company documents with AI-powered retrieval", { x: 0.7, y: 0.75, w: 8, h: 0.3, fontSize: 12, fontFace: "Arial", color: C.dim, margin: 0 });

  const kbs = [
    { name: "Corporate Knowledge", source: "haadthip-ks", docs: "23 docs", topics: "MFA · VPN · Email O365 · Meeting Room · IT Policy · DLP", color: C.blue, tip: 'Type / → "Haadthip Knowledge"' },
    { name: "SAP HIP Manuals", source: "sap-docs-ks", docs: "32 docs", topics: "Tcodes · Procedures · Branch Operations · Accounting", color: C.green, tip: 'Type / → "SAP Knowledge"' },
    { name: "Investor Relations", source: "ir-docs-ks", docs: "31 docs", topics: "Annual Report · Form 56-1 · Financial Data · MD&A · AGM", color: C.purple, tip: 'Type / → "IR Knowledge"' },
    { name: "HR Knowledge", source: "mihcm-hr-ks", docs: "~20 docs", topics: "Leave · Benefits · Compensation · Work Rules · Policies", color: C.orange, tip: 'Type / → "HR Knowledge"' },
  ];

  kbs.forEach((kb, i) => {
    const y = 1.2 + i * 1.0;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y, w: 8.5, h: 0.85, fill: { color: C.surface }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y, w: 0.06, h: 0.85, fill: { color: kb.color } });
    s.addText(kb.name, { x: 1.0, y: y + 0.06, w: 3.5, h: 0.28, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
    s.addText(kb.source + " · " + kb.docs, { x: 4.5, y: y + 0.06, w: 2, h: 0.28, fontSize: 10, fontFace: "Consolas", color: C.dim, margin: 0 });
    s.addText(kb.topics, { x: 1.0, y: y + 0.38, w: 7, h: 0.22, fontSize: 10, fontFace: "Arial", color: C.text, margin: 0 });
    s.addText(kb.tip, { x: 1.0, y: y + 0.6, w: 5, h: 0.2, fontSize: 9, fontFace: "Arial", color: C.teal, italic: true, margin: 0 });
  });

  s.addText("How: Type / in chat box → select Knowledge Base → ask your question in Thai or English", { x: 0.7, y: 5.2, w: 8.5, h: 0.25, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
}

// ============================================================
// Slide 6: Tools & Functions
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Tools & Functions", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
  s.addText("Built-in tools — model can choose which to call automatically (Agentic Mode)", { x: 0.7, y: 0.75, w: 8, h: 0.3, fontSize: 12, fontFace: "Arial", color: C.dim, margin: 0 });

  // E-Expense
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 1.2, w: 4.0, h: 1.8, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 1.2, w: 0.06, h: 1.8, fill: { color: C.red } });
  s.addText("🛫  E-Expense FAQ", { x: 1.0, y: 1.3, w: 3.4, h: 0.3, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText("42 FAQ documents — ask about:", { x: 1.0, y: 1.65, w: 3.4, h: 0.2, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
  const expenseItems = ["Travel Plans (แผนเดินทาง)", "Cash Advances (เบิกทดรองจ่าย)", "Expense Clearing (เคลียร์ค่าใช้จ่าย)", "Medical Claims (ค่ารักษาพยาบาล)"];
  expenseItems.forEach((item, i) => {
    s.addText("• " + item, { x: 1.2, y: 1.9 + i * 0.22, w: 3, h: 0.18, fontSize: 10, fontFace: "Arial", color: C.text, margin: 0 });
  });
  s.addText("Just ask naturally: \"ขออนุมัติเดินทางต่างประเทศ\"", { x: 1.0, y: 2.78, w: 3.4, h: 0.18, fontSize: 9, fontFace: "Arial", color: C.teal, italic: true, margin: 0 });

  // Tool system
  s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y: 1.2, w: 4.3, h: 1.8, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y: 1.2, w: 0.06, h: 1.8, fill: { color: C.purple } });
  s.addText("🔧  How Tools Work", { x: 5.3, y: 1.3, w: 3.6, h: 0.3, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText([
    { text: '1. You ask: "MFA on Android?"', options: { breakLine: true } },
    { text: '2. GPT decides: "Need to search KB"', options: { breakLine: true } },
    { text: '3. Calls search tool → gets 3 docs', options: { breakLine: true } },
    { text: '4. GPT reads docs → answers you', options: { breakLine: true } },
    { text: '5. You see the answer + sources', options: {} },
  ], { x: 5.5, y: 1.7, w: 3.5, h: 1.2, fontSize: 10, fontFace: "Arial", color: C.text, margin: 0 });

  // Available tools summary
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.25, w: 8.5, h: 0.45, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.25, w: 0.06, h: 0.45, fill: { color: C.blue } });
  s.addText("Available Tools", { x: 1.0, y: 3.3, w: 3, h: 0.2, fontSize: 12, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText("KB Search (4 corpuses)  ·  E-Expense FAQ  ·  Web Search  ·  Code Interpreter  ·  (more coming)", { x: 1.0, y: 3.5, w: 7.8, h: 0.18, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });

  // Filter function note
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.95, w: 8.5, h: 0.45, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.95, w: 0.06, h: 0.45, fill: { color: C.green } });
  s.addText("Token Tracking Filter", { x: 1.0, y: 4.0, w: 3, h: 0.2, fontSize: 12, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText("Every request & response is logged — tracks model, user, token count, and latency", { x: 1.0, y: 4.2, w: 7.8, h: 0.18, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
}

// ============================================================
// Slide 7: Model Selection & Custom Prompts
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Model Selection & Custom Prompts", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });

  // Model table
  const models = [
    { name: "gpt-5.4-nano", cost: "$ Cheapest", use: "Simple queries, KB planning, quick lookups", color: C.green },
    { name: "gpt-5.4-mini", cost: "$$ Balanced", use: "General chat, everyday use, tools/agents", color: C.blue },
    { name: "gpt-5.4", cost: "$$$ Best quality", use: "Complex Thai, Pipe final answers, reasoning", color: C.purple },
    { name: "gpt-5.2", cost: "$$ Legacy", use: "Fallback compatibility", color: C.orange },
  ];

  s.addText("Which Model Should I Use?", { x: 0.7, y: 0.85, w: 4, h: 0.3, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  models.forEach((m, i) => {
    const y = 1.25 + i * 0.45;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y, w: 8.5, h: 0.37, fill: { color: C.surface }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y, w: 0.05, h: 0.37, fill: { color: m.color } });
    s.addText(m.name, { x: 0.95, y: y + 0.05, w: 2.0, h: 0.27, fontSize: 12, fontFace: "Consolas", color: m.color, bold: true, margin: 0 });
    s.addText(m.cost, { x: 3.0, y: y + 0.05, w: 1.2, h: 0.27, fontSize: 11, fontFace: "Arial", color: C.dim, margin: 0 });
    s.addText(m.use, { x: 4.3, y: y + 0.05, w: 4.5, h: 0.27, fontSize: 11, fontFace: "Arial", color: C.text, margin: 0 });
  });

  // Custom System Prompts
  s.addText("Custom System Prompts", { x: 0.7, y: 3.25, w: 4, h: 0.3, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText("Control how the AI behaves — tone, expertise, language, format", { x: 0.7, y: 3.55, w: 6, h: 0.2, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });

  // How to set
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.85, w: 8.5, h: 1.5, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.85, w: 0.06, h: 1.5, fill: { color: C.teal } });
  s.addText("How to Set:", { x: 1.0, y: 3.92, w: 2, h: 0.22, fontSize: 11, fontFace: "Arial", color: C.teal, bold: true, margin: 0 });

  const promptSteps = [
    "1. Settings → Models → click the pencil ✏️ next to a model",
    "2. Scroll to \"System Prompt\" text box",
    "3. Write your custom instructions (Thai or English)",
    '4. Example: "คุณเป็นผู้ช่วยฝ่าย IT ของ Haadthip ตอบเป็นภาษาไทย สุภาพ กระชับ"',
    '5. Save → start a new chat with that model → prompt is applied',
  ];
  promptSteps.forEach((step, i) => {
    s.addText(step, { x: 1.0, y: 4.2 + i * 0.25, w: 7.8, h: 0.2, fontSize: 10, fontFace: "Arial", color: C.text, margin: 0 });
  });
}

// ============================================================
// Slide 8: LiteLLM Dashboard
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("LiteLLM Dashboard", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });

  s.addImage({ path: path.join(SCREENSHOTS, "litellm-dashboard.png"), x: 0.4, y: 0.95, w: 5.5, h: 3.7, sizing: { type: "contain", w: 5.5, h: 3.7 } });

  const features = [
    ["Token Usage", "Track per user, model, team — real-time"],
    ["Cost Monitoring", "Budget limits, spend alerts, per-project"],
    ["API Keys", "Generate keys for dev tools & CI/CD"],
    ["Audit Logs", "Every request logged — who, what, when"],
    ["Rate Limiting", "Prevent API abuse, set per-user limits"],
    ["Model Dashboard", "5 models: Nano, Mini, 5.4, 5.2, Embedding"],
  ];

  const startX = 6.2;
  features.forEach(([title, desc], i) => {
    const y = 0.95 + i * 0.57;
    s.addShape(pres.shapes.RECTANGLE, { x: startX, y, w: 3.3, h: 0.46, fill: { color: C.surface }, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: startX, y, w: 0.05, h: 0.46, fill: { color: C.green } });
    s.addText(title, { x: startX + 0.2, y: y + 0.04, w: 2.8, h: 0.2, fontSize: 12, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
    s.addText(desc, { x: startX + 0.2, y: y + 0.25, w: 2.8, h: 0.17, fontSize: 9, fontFace: "Arial", color: C.dim, margin: 0 });
  });

  s.addText([
    { text: "Dashboard: ", options: { color: C.dim } },
    { text: "genie.haadthip.com/litellm/ui", options: { color: C.blue } },
  ], { x: 0.7, y: 4.85, w: 5, h: 0.25, fontSize: 10, fontFace: "Consolas", margin: 0 });
  s.addText("Login: admin / Master Key  ·  SSO with Entra ID coming soon", { x: 0.7, y: 5.1, w: 5, h: 0.25, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
}

// ============================================================
// Slide 9: Integration — Dev Tools
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Integration — Connect from Anywhere", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });

  // Browser
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 1.0, w: 8.5, h: 0.85, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 1.0, w: 0.06, h: 0.85, fill: { color: C.blue } });
  s.addText("🌐  Web Browser (End Users)", { x: 1.0, y: 1.08, w: 4, h: 0.25, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText("genie.haadthip.com → Sign in with Microsoft → Start chatting. No installation. Works on mobile.", { x: 1.0, y: 1.38, w: 7.8, h: 0.2, fontSize: 11, fontFace: "Arial", color: C.dim, margin: 0 });
  s.addText("Auth: Entra ID SSO (OIDC) — auto signup for all @haadthip.com accounts", { x: 1.0, y: 1.6, w: 7.8, h: 0.2, fontSize: 10, fontFace: "Arial", color: C.teal, margin: 0 });

  // Dev Tools
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 2.1, w: 8.5, h: 1.35, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 2.1, w: 0.06, h: 1.35, fill: { color: C.green } });
  s.addText("💻  Developer Tools & IDE", { x: 1.0, y: 2.18, w: 4, h: 0.25, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  const devTools = [
    ["Continue.dev (VS Code)", "OpenAI provider → URL: genie.haadthip.com/litellm/v1"],
    ["Cursor / Windsurf", "OpenAI-compatible endpoint → API key from LiteLLM"],
    ["Claude Code / Gemini CLI", "Set OPENAI_BASE_URL → genie.haadthip.com/litellm/v1"],
    ["Custom Script / curl", "POST /v1/chat/completions → Bearer your-api-key"],
  ];
  devTools.forEach(([t, d], i) => {
    s.addText(t, { x: 1.2, y: 2.5 + i * 0.24, w: 2.8, h: 0.18, fontSize: 10, fontFace: "Consolas", color: C.text, margin: 0 });
    s.addText(d, { x: 4.1, y: 2.5 + i * 0.24, w: 4.5, h: 0.18, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
  });

  // API Key generation
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.7, w: 8.5, h: 0.65, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.7, w: 0.06, h: 0.65, fill: { color: C.orange } });
  s.addText("🔑  How to Get an API Key", { x: 1.0, y: 3.78, w: 4, h: 0.22, fontSize: 12, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addText("LiteLLM Dashboard → Keys → Create Key → Set budget & rate limit → Copy to your tool. Each key can be scoped per user/team with individual limits.", { x: 1.0, y: 4.03, w: 7.8, h: 0.25, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });

  // Endpoint summary
  s.addText("API Endpoint:  genie.haadthip.com/litellm/v1", { x: 0.7, y: 4.6, w: 5, h: 0.25, fontSize: 11, fontFace: "Consolas", color: C.blue, bold: true, margin: 0 });
}

// ============================================================
// Slide 10: Key Numbers
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Key Numbers", { x: 0.7, y: 0.4, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });

  const stats = [
    { num: "5", label: "AI Models", sub: "GPT-5.4 Nano → 5.4", color: C.green },
    { num: "4", label: "Knowledge Bases", sub: "Corporate · SAP · IR · HR", color: C.blue },
    { num: "3", label: "Databases", sub: "open_webui · docwise · litellm", color: C.purple },
    { num: "1", label: "SSO Provider", sub: "Microsoft Entra ID", color: C.teal },
  ];

  stats.forEach((st, i) => {
    const x = 0.7 + i * 2.2;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.3, w: 1.9, h: 1.8, fill: { color: C.surface }, shadow: makeShadow() });
    s.addText(st.num, { x, y: 1.4, w: 1.9, h: 0.8, fontSize: 48, fontFace: "Arial Black", color: st.color, align: "center", margin: 0 });
    s.addText(st.label, { x, y: 2.2, w: 1.9, h: 0.25, fontSize: 12, fontFace: "Arial", color: C.white, bold: true, align: "center", margin: 0 });
    s.addText(st.sub, { x, y: 2.5, w: 1.9, h: 0.3, fontSize: 9, fontFace: "Arial", color: C.dim, align: "center", margin: 0 });
  });

  // URLs table
  s.addText("URLs & Access Points", { x: 0.7, y: 3.4, w: 4, h: 0.3, fontSize: 16, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  const urls = [
    ["Genie (Chat UI)", "genie.haadthip.com"],
    ["LiteLLM API", "genie.haadthip.com/litellm/v1"],
    ["LiteLLM Dashboard", "genie.haadthip.com/litellm/ui"],
  ];
  urls.forEach(([label, url], i) => {
    const y = 3.8 + i * 0.3;
    s.addText(label, { x: 0.7, y, w: 2.5, h: 0.22, fontSize: 11, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
    s.addText(url, { x: 3.3, y, w: 4, h: 0.22, fontSize: 11, fontFace: "Consolas", color: C.blue, margin: 0 });
  });
}

// ============================================================
// Slide 11: Resources & Community
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Resources & Community", { x: 0.7, y: 0.3, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
  s.addText("Explore existing tools, functions, and prompts — install in 1 click or copy-paste", { x: 0.7, y: 0.75, w: 8, h: 0.3, fontSize: 12, fontFace: "Arial", color: C.dim, margin: 0 });

  // Column 1: Official
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 2.8, h: 3.6, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 2.8, h: 0.06, fill: { color: C.blue } });
  s.addText("🌟  Official", { x: 0.7, y: 1.35, w: 2.4, h: 0.25, fontSize: 13, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  const official = [
    ["Community Hub", "openwebui.com", "Browse & 1-click import"],
    ["Functions Repo", "github.com/open-webui/functions", "Core-team curated"],
    ["Plugin Docs", "docs.openwebui.com/plugin", "How to build your own"],
  ];
  official.forEach(([title, url, desc], i) => {
    const y = 1.7 + i * 0.95;
    s.addText(title, { x: 0.7, y, w: 2.4, h: 0.18, fontSize: 10, fontFace: "Arial", color: C.teal, bold: true, margin: 0 });
    s.addText(url, { x: 0.7, y: y + 0.2, w: 2.4, h: 0.16, fontSize: 7, fontFace: "Consolas", color: C.blue, margin: 0 });
    s.addText(desc, { x: 0.7, y: y + 0.38, w: 2.4, h: 0.15, fontSize: 8, fontFace: "Arial", color: C.dim, margin: 0 });
  });

  // Column 2: Community Tools
  s.addShape(pres.shapes.RECTANGLE, { x: 3.55, y: 1.2, w: 3.2, h: 3.6, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.55, y: 1.2, w: 3.2, h: 0.06, fill: { color: C.green } });
  s.addText("🛠️  Community Tools", { x: 3.75, y: 1.35, w: 2.8, h: 0.25, fontSize: 13, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  const tools = [
    ["Haervwe/tools", "Modular tools, pipes, filters"],
    ["Skyzi000/extensions", "Sub Agent Tool"],
    ["suurt8ll/functions", "Gemini, Venice.ai pipes"],
    ["owndev/Functions", "Real-world pipelines"],
    ["mplogas/open-webui", "GitHub reader tools"],
    ["bgeneto/functions", "Community registry"],
  ];
  tools.forEach(([title, desc], i) => {
    const y = 1.72 + i * 0.48;
    s.addText(title, { x: 3.75, y, w: 2.6, h: 0.16, fontSize: 9, fontFace: "Consolas", color: C.green, margin: 0 });
    s.addText(desc, { x: 3.75, y: y + 0.18, w: 2.6, h: 0.14, fontSize: 8, fontFace: "Arial", color: C.dim, margin: 0 });
  });

  // Column 3: Prompts + Install
  s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 1.2, w: 2.5, h: 1.6, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 1.2, w: 2.5, h: 0.06, fill: { color: C.purple } });
  s.addText("📝  Prompts", { x: 7.15, y: 1.35, w: 2.1, h: 0.25, fontSize: 13, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  const prompts = [
    ["Prompt Library", "danielrosehill/OpenWebUI-Prompt-Library"],
    ["Model Index", "danielrosehill/Open-Web-UI-Model-Index"],
  ];
  prompts.forEach(([title, url], i) => {
    const y = 1.72 + i * 0.62;
    s.addText(title, { x: 7.15, y, w: 2.1, h: 0.16, fontSize: 9, fontFace: "Arial", color: C.purple, bold: true, margin: 0 });
    s.addText(url, { x: 7.15, y: y + 0.2, w: 2.1, h: 0.2, fontSize: 7, fontFace: "Consolas", color: C.blue, margin: 0 });
  });

  // Install methods
  s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 3.05, w: 2.5, h: 1.75, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 3.05, w: 2.5, h: 0.06, fill: { color: C.orange } });
  s.addText("⚡  Install", { x: 7.15, y: 3.2, w: 2.1, h: 0.25, fontSize: 13, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  s.addText("1-Click:", { x: 7.15, y: 3.55, w: 2.1, h: 0.16, fontSize: 9, fontFace: "Arial", color: C.orange, bold: true, margin: 0 });
  s.addText("openwebui.com → Find → Get", { x: 7.15, y: 3.72, w: 2.1, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.dim, margin: 0 });
  s.addText("Manual:", { x: 7.15, y: 4.0, w: 2.1, h: 0.16, fontSize: 9, fontFace: "Arial", color: C.orange, bold: true, margin: 0 });
  s.addText("Copy .py → Workspace → Paste → Save", { x: 7.15, y: 4.17, w: 2.1, h: 0.3, fontSize: 8, fontFace: "Arial", color: C.dim, margin: 0 });

  s.addText("All repos: github.com search \"open-webui tools\" or \"open-webui functions\"", { x: 0.7, y: 5.0, w: 8.5, h: 0.25, fontSize: 9, fontFace: "Arial", color: C.dim, italic: true, margin: 0 });
}

// ============================================================
// Slide 12: Q&A
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("Frequently Asked Questions", { x: 0.7, y: 0.4, w: 8, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });

  const faqs = [
    ["Q: ข้อมูลปลอดภัยไหม?", "Azure Thailand (Southeast Asia), Private Endpoint, ทุกอย่างอยู่ภายใน Azure ของ Haadthip เท่านั้น"],
    ["Q: AI เอาเอกสารบริษัทไป train ต่อไหม?", "ไม่ — Azure OpenAI ไม่ใช้ข้อมูลลูกค้าเทรนโมเดล (Enterprise data protection)"],
    ["Q: ใช้มือถือได้ไหม?", "ได้ — Open WebUI responsive, เปิด browser มือถือเข้า genie.haadthip.com ได้เลย"],
    ["Q: คนนอกเข้าได้ไหม?", "ไม่ได้ — ต้องมี @haadthip.com account ผ่าน Microsoft Entra ID SSO เท่านั้น"],
    ["Q: ถ้า AI ตอบผิด?", "AI อาจ hallucinate — ตรวจสอบข้อมูลสำคัญกับต้นทางเสมอ. ทุกคำตอบระบุแหล่งที่มา"],
    ["Q: เพิ่มเอกสารใหม่ยังไง?", "ทีม IT อัปโหลดผ่าน ingestion pipeline → index ใน AI Search → ใช้ได้ทันที"],
    ["Q: ดู token usage ได้ที่ไหน?", "LiteLLM Dashboard (genie.haadthip.com/litellm/ui) หรือ Admin Panel ใน Open WebUI"],
  ];

  faqs.forEach(([q, a], i) => {
    const y = 1.1 + i * 0.55;
    s.addText(q, { x: 0.7, y, w: 8.5, h: 0.22, fontSize: 11, fontFace: "Arial", color: C.orange, bold: true, margin: 0 });
    s.addText(a, { x: 0.7, y: y + 0.23, w: 8.5, h: 0.22, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
  });
}

// ============================================================
// Slide 13: Next Steps + Thank You
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Left: Next Steps
  s.addText("Next Steps", { x: 0.7, y: 0.4, w: 4, h: 0.5, fontSize: 24, fontFace: "Arial Black", color: C.teal, margin: 0 });

  const nextSteps = [
    "Add pilot users to Internal User group",
    "Collect feedback: model quality, KB coverage",
    "Setup budget limits per user/team",
    "Integrate with Continue.dev for developers",
    "Add more Knowledge Bases as needed",
    "Prepare production deployment plan",
  ];
  nextSteps.forEach((step, i) => {
    s.addText("→  " + step, { x: 0.9, y: 1.1 + i * 0.35, w: 4.5, h: 0.25, fontSize: 11, fontFace: "Arial", color: C.text, margin: 0 });
  });

  // Right: Thank You
  s.addShape(pres.shapes.RECTANGLE, { x: 6.0, y: 1.1, w: 0.06, h: 1.4, fill: { color: C.teal } });
  s.addText("Thank You", { x: 6.4, y: 1.1, w: 3, h: 0.7, fontSize: 36, fontFace: "Arial Black", color: C.white, bold: true, margin: 0 });
  s.addText("Questions & Feedback", { x: 6.4, y: 1.8, w: 3, h: 0.4, fontSize: 16, fontFace: "Arial", color: C.teal, margin: 0 });

  // Bottom links
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.4, w: 8.5, h: 1.6, fill: { color: C.surface }, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.4, w: 0.06, h: 1.6, fill: { color: C.blue } });

  s.addText("Quick Links", { x: 1.0, y: 3.5, w: 4, h: 0.25, fontSize: 14, fontFace: "Arial", color: C.white, bold: true, margin: 0 });

  const links = [
    ["Genie Chat", "genie.haadthip.com"],
    ["LiteLLM Dashboard", "genie.haadthip.com/litellm/ui"],
    ["LiteLLM API", "genie.haadthip.com/litellm/v1"],
    ["Documentation", "CONTEXT.md (internal)"],
  ];
  links.forEach(([label, url], i) => {
    const y = 3.85 + i * 0.28;
    s.addText(label, { x: 1.2, y, w: 2.5, h: 0.22, fontSize: 11, fontFace: "Arial", color: C.text, margin: 0 });
    s.addText(url, { x: 3.8, y, w: 5, h: 0.22, fontSize: 11, fontFace: "Consolas", color: C.blue, margin: 0 });
  });

  s.addText("EnterpriseChat POC · Haadthip PCL · Confidential", { x: 0.7, y: 5.2, w: 8, h: 0.25, fontSize: 10, fontFace: "Arial", color: C.dim, margin: 0 });
}

// ============================================================
pres.writeFile({ fileName: OUT }).then(() => {
  console.log("✅ PPTX created:", OUT);
}).catch(err => {
  console.error("❌", err);
});
