import os
import sys
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Microsoft Learn / Azure Architecture Theme Colors ────────────────────────
COLOR_BG = RGBColor(248, 249, 250)         # #F8F9FA Soft Slate Light
COLOR_WHITE = RGBColor(255, 255, 255)     # #FFFFFF Pure White Card
COLOR_AZURE_BLUE = RGBColor(0, 120, 212)  # #0078D4 Microsoft Azure Blue
COLOR_NAVY_DARK = RGBColor(16, 37, 66)    # #102542 Dark Navy Header
COLOR_SLATE_DARK = RGBColor(36, 41, 47)   # #24292F Primary Text
COLOR_MUTED_TEXT = RGBColor(90, 105, 120) # #5A6978 Secondary / Muted Text
COLOR_BORDER = RGBColor(226, 232, 240)    # #E2E8F0 Subtle Border Gray
COLOR_CARD_ALT = RGBColor(241, 245, 249)  # #F1F5F9 Alternate Card
COLOR_ACCENT_TEAL = RGBColor(0, 164, 180) # #00A4B4 Azure AI / Search Accent
COLOR_ACCENT_GREEN = RGBColor(16, 124, 65)# #107C41 Success / Ingestion Green
COLOR_ACCENT_ORANGE = RGBColor(216, 59, 1)# #D83B01 Security / Warning Orange
COLOR_TAG_BG = RGBColor(234, 243, 253)    # #EAF3FD Azure Badge BG
COLOR_TAG_TEXT = RGBColor(0, 90, 158)    # #005A9E Azure Badge Text

def create_deck(output_path="azure_architecture_enterprise_chat.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.fill.background()
        return bg

    def add_ms_header(slide, title, category="AZURE ARCHITECTURE CENTER", subtitle=None):
        # Top banner category badge
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.3))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(9.5)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_AZURE_BLUE

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.68), Inches(11.7), Inches(0.6))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(20)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_NAVY_DARK

        if subtitle:
            p_sub = tf_title.add_paragraph()
            p_sub.text = subtitle
            p_sub.font.size = Pt(11)
            p_sub.font.bold = False
            p_sub.font.color.rgb = COLOR_MUTED_TEXT

        # Divider line
        div = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.015))
        div.fill.solid()
        div.fill.fore_color.rgb = COLOR_BORDER
        div.line.fill.background()

    def add_card(slide, left, top, width, height, title="", title_color=COLOR_NAVY_DARK, bg_color=COLOR_WHITE, border_color=COLOR_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        
        if title:
            tb = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.12), width - Inches(0.3), Inches(0.35))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = title_color
            
        return card

    # =========================================================================
    # SLIDE 1: Title & Executive Summary (Microsoft Learn Hero Style)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    # Hero top accent bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.1))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_AZURE_BLUE
    bar.line.fill.background()

    # Title Box
    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(0.9), Inches(11.333), Inches(2.2))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "AZURE ARCHITECTURE REFERENCE GUIDE"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_AZURE_BLUE
    p0.space_after = Pt(10)

    p1 = tf1.add_paragraph()
    p1.text = "HaadThip Enterprise AI Platform Architecture"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_NAVY_DARK

    p2 = tf1.add_paragraph()
    p2.text = "End-to-End System Architecture, Data Flows, and Master Persistence for EnterpriseChat (Genie) & DocWise"
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_MUTED_TEXT
    p2.space_before = Pt(8)

    # 3 Summary Cards
    col_w = Inches(3.6)
    gap = Inches(0.26)
    top_pos = Inches(3.2)
    h_pos = Inches(3.5)

    # Card 1: EnterpriseChat (Genie)
    add_card(s1, Inches(1.0), top_pos, col_w, h_pos, "1. EnterpriseChat (Genie)", COLOR_AZURE_BLUE)
    c1_txt = s1.shapes.add_textbox(Inches(1.15), top_pos + Inches(0.55), col_w - Inches(0.3), h_pos - Inches(0.7))
    tf_c1 = c1_txt.text_frame
    tf_c1.word_wrap = True
    tf_c1.margin_left = tf_c1.margin_top = tf_c1.margin_right = tf_c1.margin_bottom = 0
    items_c1 = [
        ("Core Role", "Conversational AI assistant integrated seamlessly into Microsoft Teams & Web Browser."),
        ("Frontend & UI", "Open WebUI v0.11.0 with customized Teams SDK v2 Popup SSO bridge (`teams-auth.html`)."),
        ("AI Gateway", "LiteLLM Proxy with Local Prompt Caching (90% cost cut) and Token/Budget tracking."),
        ("RAG Engine", "Custom `AzureAISearchClient` replacing ChromaDB with namespace consolidation.")
    ]
    for k, v in items_c1:
        p = tf_c1.add_paragraph() if tf_c1.paragraphs[0].text else tf_c1.paragraphs[0]
        p.text = f"• {k}: "
        p.font.bold = True
        p.font.size = Pt(10)
        p.font.color.rgb = COLOR_SLATE_DARK
        run = p.add_run()
        run.text = v
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_MUTED_TEXT
        p.space_after = Pt(6)

    # Card 2: DocWise Intelligent Docs
    add_card(s1, Inches(1.0) + col_w + gap, top_pos, col_w, h_pos, "2. DocWise Document System", COLOR_ACCENT_TEAL)
    c2_txt = s1.shapes.add_textbox(Inches(1.0) + col_w + gap + Inches(0.15), top_pos + Inches(0.55), col_w - Inches(0.3), h_pos - Inches(0.7))
    tf_c2 = c2_txt.text_frame
    tf_c2.word_wrap = True
    tf_c2.margin_left = tf_c2.margin_top = tf_c2.margin_right = tf_c2.margin_bottom = 0
    items_c2 = [
        ("Core Role", "Automated enterprise document extraction, classification, and summarization platform."),
        ("Ingestion Pipeline", "Azure Document Intelligence (prebuilt-read) + Semantic Chunking."),
        ("Vector Indexing", "Dedicated Azure AI Search index (`docwise-docs-v2`) with HNSW vector search."),
        ("App Backend", "Django-based document admin and analytics pipeline (`app-docwise-poc-sea`).")
    ]
    for k, v in items_c2:
        p = tf_c2.add_paragraph() if tf_c2.paragraphs[0].text else tf_c2.paragraphs[0]
        p.text = f"• {k}: "
        p.font.bold = True
        p.font.size = Pt(10)
        p.font.color.rgb = COLOR_SLATE_DARK
        run = p.add_run()
        run.text = v
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_MUTED_TEXT
        p.space_after = Pt(6)

    # Card 3: Cloud Landing Zone & Security
    add_card(s1, Inches(1.0) + (col_w + gap)*2, top_pos, col_w, h_pos, "3. Azure Landing Zone & Security", COLOR_ACCENT_ORANGE)
    c3_txt = s1.shapes.add_textbox(Inches(1.0) + (col_w + gap)*2 + Inches(0.15), top_pos + Inches(0.55), col_w - Inches(0.3), h_pos - Inches(0.7))
    tf_c3 = c3_txt.text_frame
    tf_c3.word_wrap = True
    tf_c3.margin_left = tf_c3.margin_top = tf_c3.margin_right = tf_c3.margin_bottom = 0
    items_c3 = [
        ("VNet Isolation", "`VNET-HTC-SANBOX-SEA` with strict Zero-Outbound policy (Blocks public egress)."),
        ("Identity & SSO", "Microsoft Entra ID (OIDC) with Pre-Authorized Teams client scopes."),
        ("Private Access", "PostgreSQL & AI Search secured via Private Endpoints (Public Access Disabled)."),
        ("Multi-DB Isolation", "Strict separation of `open_webui`, `litellm`, and `docwise` schemas.")
    ]
    for k, v in items_c3:
        p = tf_c3.add_paragraph() if tf_c3.paragraphs[0].text else tf_c3.paragraphs[0]
        p.text = f"• {k}: "
        p.font.bold = True
        p.font.size = Pt(10)
        p.font.color.rgb = COLOR_SLATE_DARK
        run = p.add_run()
        run.text = v
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_MUTED_TEXT
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 2: 3-Zone Architecture & Security Boundaries
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_ms_header(s2, "3-Zone Enterprise Landing Zone Architecture", "AZURE CLOUD SECURITY BOUNDARIES", 
                  "Isolation model separating Client Ingress, Workload VNet, and Managed Data & AI Platforms")

    zone_w = Inches(3.75)
    zone_h = Inches(5.6)
    zone_gap = Inches(0.24)
    zone_top = Inches(1.5)

    # Zone 1: Ingress & Identity
    z1 = add_card(s2, Inches(0.8), zone_top, zone_w, zone_h, "Zone 1: Ingress & Identity", COLOR_AZURE_BLUE, COLOR_CARD_ALT)
    z1_tb = s2.shapes.add_textbox(Inches(0.95), zone_top + Inches(0.55), zone_w - Inches(0.3), zone_h - Inches(0.7))
    tf_z1 = z1_tb.text_frame
    tf_z1.word_wrap = True
    tf_z1.margin_left = tf_z1.margin_top = tf_z1.margin_right = tf_z1.margin_bottom = 0

    z1_content = [
        ("Microsoft Teams Client", "Embedded App Tab (`genie.haadthip.com`) using Teams SDK v2 Popup Authentication."),
        ("Corporate Web Users", "Direct HTTPS Web Browser access via Azure Application Gateway / Custom Domain."),
        ("Microsoft Entra ID (IdP)", "`appreg-entchat-owui-poc` handling OAuth 2.0 / OIDC user authentication & token issuance."),
        ("Teams Pre-Auth", "Pre-authorized client IDs for silent & popup SSO without leaving corporate perimeter.")
    ]
    for title, desc in z1_content:
        p = tf_z1.add_paragraph() if tf_z1.paragraphs[0].text else tf_z1.paragraphs[0]
        p.text = f"■ {title}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_AZURE_BLUE
        p2 = tf_z1.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(10)

    # Zone 2: Workload VNet
    z2 = add_card(s2, Inches(0.8) + zone_w + zone_gap, zone_top, zone_w, zone_h, "Zone 2: Workload VNet (Subnet)", COLOR_NAVY_DARK, COLOR_WHITE)
    z2_tb = s2.shapes.add_textbox(Inches(0.8) + zone_w + zone_gap + Inches(0.15), zone_top + Inches(0.55), zone_w - Inches(0.3), zone_h - Inches(0.7))
    tf_z2 = z2_tb.text_frame
    tf_z2.word_wrap = True
    tf_z2.margin_left = tf_z2.margin_top = tf_z2.margin_right = tf_z2.margin_bottom = 0

    z2_content = [
        ("VNet Integration", "`VNET-HTC-SANBOX-SEA` / `SNET-HTC-SANDBOX-APP-SEA` enforces strict private perimeter."),
        ("Open WebUI (Genie)", "Linux Container (`app-entchat-owui-poc-sand`) running on App Service B2. Orchestrates chats & RAG."),
        ("LiteLLM AI Gateway", "Linux Container (`app-litellm-poc-sand`) managing prompt caching, model routing & MCP servers."),
        ("DocWise App", "Linux Container (`app-docwise-poc-sea`) handling document workflow & content understanding."),
        ("Outbound Lockdown", "All internet egress blocked by default. NSG whitelist specifically allows Entra ID login.")
    ]
    for title, desc in z2_content:
        p = tf_z2.add_paragraph() if tf_z2.paragraphs[0].text else tf_z2.paragraphs[0]
        p.text = f"■ {title}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_NAVY_DARK
        p2 = tf_z2.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(8)

    # Zone 3: Data & AI Platform
    z3 = add_card(s2, Inches(0.8) + (zone_w + zone_gap)*2, zone_top, zone_w, zone_h, "Zone 3: Managed Data & AI", COLOR_ACCENT_TEAL, COLOR_CARD_ALT)
    z3_tb = s2.shapes.add_textbox(Inches(0.8) + (zone_w + zone_gap)*2 + Inches(0.15), zone_top + Inches(0.55), zone_w - Inches(0.3), zone_h - Inches(0.7))
    tf_z3 = z3_tb.text_frame
    tf_z3.word_wrap = True
    tf_z3.margin_left = tf_z3.margin_top = tf_z3.margin_right = tf_z3.margin_bottom = 0

    z3_content = [
        ("Azure AI Foundry", "`aif-entchat-poc-sand` hosting GPT-5.4 family + `text-embedding-3-large` via Azure Service Endpoints."),
        ("Azure AI Search", "`srch-entchat-poc-sand` (Standard Tier) with Private Endpoint. Hybrid vector + BM25 search."),
        ("PostgreSQL Flexible", "`psql-entchat-poc-sand` (B1ms, Private Endpoint). Multi-tenant databases with strict isolation."),
        ("Azure Blob Storage", "`staentchatdoc` storing raw source documents, uploads, cost reports, and system artifacts.")
    ]
    for title, desc in z3_content:
        p = tf_z3.add_paragraph() if tf_z3.paragraphs[0].text else tf_z3.paragraphs[0]
        p.text = f"■ {title}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_ACCENT_TEAL
        p2 = tf_z3.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(10)

    # =========================================================================
    # SLIDE 3: EnterpriseChat (Genie) Deep Dive & End-to-End Chat Flow
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_ms_header(s3, "EnterpriseChat (Genie) Architecture & Request Flow", "SERVICE-TO-SERVICE INTERACTION", 
                  "End-to-end trace of User Query, Authentication, Prompt Caching, Vector Search, and LLM Inference")

    # Left Column: Service Components (W: 5.6)
    left_w = Inches(5.6)
    add_card(s3, Inches(0.8), Inches(1.5), left_w, Inches(5.6), "Genie Core Components", COLOR_AZURE_BLUE)
    g_tb = s3.shapes.add_textbox(Inches(0.95), Inches(2.05), left_w - Inches(0.3), Inches(4.9))
    tf_g = g_tb.text_frame
    tf_g.word_wrap = True
    tf_g.margin_left = tf_g.margin_top = tf_g.margin_right = tf_g.margin_bottom = 0

    g_comps = [
        ("Open WebUI (Custom Image: `entchat-owui`)", 
         "• Upstream v0.11.0 with baked-in patches (`app/patches/client.py`).\n• Hosts Teams SSO popup handler (`teams-auth.html`) and user session state.\n• Custom vector backend interface implementing 10 methods of `VectorDBBase`."),
        ("LiteLLM Proxy (`app-litellm-poc-sand`)",
         "• Centralized LLM Gateway on port 4000.\n• Local Cache (TTL 3600s) reducing repetitive prompt cost by 90%.\n• Model cost monitoring, token accounting, and budget enforcement.\n• MCP Tool Servers: `postgres`, `filesystem`, `time`, `context7`."),
        ("Azure AI Foundry Deployments",
         "• `deploy-gpt-5.4-mini` ($0.75/1M in): Main conversational engine.\n• `deploy-gpt-5.4-nano` ($0.20/1M in): Fast query planning & tool routing.\n• `deploy-gpt-5.4` ($2.50/1M in): Complex RAG synthesis & final pipe answers.\n• `deploy-embedding-3-large`: 3072-dimension high-accuracy vector embeddings.")
    ]
    for title, desc in g_comps:
        p = tf_g.add_paragraph() if tf_g.paragraphs[0].text else tf_g.paragraphs[0]
        p.text = title
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_NAVY_DARK
        p2 = tf_g.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(8)

    # Right Column: Sequential Dataflow Steps (W: 5.9)
    right_w = Inches(5.9)
    add_card(s3, Inches(6.6), Inches(1.5), right_w, Inches(5.6), "End-to-End Chat Data Flow", COLOR_ACCENT_TEAL)
    flow_tb = s3.shapes.add_textbox(Inches(6.75), Inches(2.05), right_w - Inches(0.3), Inches(4.9))
    tf_flow = flow_tb.text_frame
    tf_flow.word_wrap = True
    tf_flow.margin_left = tf_flow.margin_top = tf_flow.margin_right = tf_flow.margin_bottom = 0

    steps = [
        ("Step 1: Ingress & Auth", "User interacts via Teams/Web. `teams-auth.html` validates Entra ID session via SDK popup and establishes session cookie."),
        ("Step 2: Embedding Generation", "User query is vectorized via `deploy-embedding-3-large` (3072 dimensions) through LiteLLM."),
        ("Step 3: Vector Search & Retrieval", "`AzureAISearchClient` queries `owui-knowledge` or `enterprise-docs-idx` using Hybrid Search (Vector HNSW + BM25) with `collection_key` OData filter."),
        ("Step 4: Prompt Construction & LiteLLM Routing", "Open WebUI combines System Prompt + Retrieved Chunks + User Message and calls LiteLLM `/v1/chat/completions`."),
        ("Step 5: Cache Check & Model Inference", "LiteLLM checks local memory cache. On cache miss, requests forward to AI Foundry (`deploy-gpt-5.4-mini`)."),
        ("Step 6: Streaming Response & Accounting", "AI Foundry streams tokens back to user; LiteLLM records token consumption & cost into PostgreSQL (`litellm` DB).")
    ]
    for step_title, step_desc in steps:
        p = tf_flow.add_paragraph() if tf_flow.paragraphs[0].text else tf_flow.paragraphs[0]
        p.text = step_title
        p.font.bold = True
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_AZURE_BLUE
        p2 = tf_flow.add_paragraph()
        p2.text = step_desc
        p2.font.size = Pt(9)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(6)

    # =========================================================================
    # SLIDE 4: DocWise & Enterprise RAG Ingestion Pipeline
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_ms_header(s4, "Intelligent Document Pipeline: Ingestion & Retrieval", "DOCUMENT UNDERSTANDING & KNOWLEDGE BASE", 
                  "Multi-stage document processing architecture from raw enterprise files to indexed vector knowledge")

    col_w4 = Inches(3.75)
    gap4 = Inches(0.24)

    # Ingestion Stage 1: Extraction
    add_card(s4, Inches(0.8), Inches(1.5), col_w4, Inches(5.6), "1. Extraction & Preprocessing", COLOR_ACCENT_GREEN)
    tb_i1 = s4.shapes.add_textbox(Inches(0.95), Inches(2.05), col_w4 - Inches(0.3), Inches(4.9))
    tf_i1 = tb_i1.text_frame
    tf_i1.word_wrap = True
    tf_i1.margin_left = tf_i1.margin_top = tf_i1.margin_right = tf_i1.margin_bottom = 0
    items_i1 = [
        ("Source Document Storage", "Raw PDFs, DOCX, and Markdown stored in Azure Blob Storage (`staentchatdoc/documents` & `uploads`)."),
        ("Document Intelligence", "Azure AI Document Intelligence (`prebuilt-read` model) extracts high-fidelity text, layout, headers, and tables."),
        ("Multi-Corpus Ingestion", "Unified ingestion pipeline (`scripts/ingest/unified.py`) processes Corporate Disclosures, HR Policies, and SAP Manuals.")
    ]
    for t, d in items_i1:
        p = tf_i1.add_paragraph() if tf_i1.paragraphs[0].text else tf_i1.paragraphs[0]
        p.text = f"■ {t}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_ACCENT_GREEN
        p2 = tf_i1.add_paragraph()
        p2.text = d
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(10)

    # Ingestion Stage 2: Chunking & Embeddings
    add_card(s4, Inches(0.8) + col_w4 + gap4, Inches(1.5), col_w4, Inches(5.6), "2. Chunking & Embeddings", COLOR_AZURE_BLUE)
    tb_i2 = s4.shapes.add_textbox(Inches(0.8) + col_w4 + gap4 + Inches(0.15), Inches(2.05), col_w4 - Inches(0.3), Inches(4.9))
    tf_i2 = tb_i2.text_frame
    tf_i2.word_wrap = True
    tf_i2.margin_left = tf_i2.margin_top = tf_i2.margin_right = tf_i2.margin_bottom = 0
    items_i2 = [
        ("Semantic Chunking", "Split via `RecursiveCharacterTextSplitter` with Markdown header splitting enabled.\n• Chunk Size: 1,000 chars\n• Chunk Overlap: 100 chars"),
        ("Tokenizer Alignment", "Calibrated with `tiktoken` (`cl100k_base`) to maximize embedding model token density."),
        ("High-Dim Embeddings", "Azure AI Foundry `text-embedding-3-large` generates 3072-dimensional vector representations.")
    ]
    for t, d in items_i2:
        p = tf_i2.add_paragraph() if tf_i2.paragraphs[0].text else tf_i2.paragraphs[0]
        p.text = f"■ {t}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_AZURE_BLUE
        p2 = tf_i2.add_paragraph()
        p2.text = d
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(10)

    # Ingestion Stage 3: Indexing & Retrieval
    add_card(s4, Inches(0.8) + (col_w4 + gap4)*2, Inches(1.5), col_w4, Inches(5.6), "3. Indexing & Hybrid Search", COLOR_ACCENT_TEAL)
    tb_i3 = s4.shapes.add_textbox(Inches(0.8) + (col_w4 + gap4)*2 + Inches(0.15), Inches(2.05), col_w4 - Inches(0.3), Inches(4.9))
    tf_i3 = tb_i3.text_frame
    tf_i3.word_wrap = True
    tf_i3.margin_left = tf_i3.margin_top = tf_i3.margin_right = tf_i3.margin_bottom = 0
    items_i3 = [
        ("Enterprise Index (`enterprise-docs-idx`)", "Master search index with 1,163+ indexed chunks across enterprise knowledge domains."),
        ("DocWise Index (`docwise-docs-v2`)", "Dedicated document processing index for deep content extraction and structured summaries."),
        ("Hybrid + Semantic Ranking", "Combines HNSW vector similarity + BM25 keyword matching with optional Semantic Re-ranking."),
        ("Enterprise Search Tool", "Open WebUI function calling tool filtering by `corpus` and `category` metadata.")
    ]
    for t, d in items_i3:
        p = tf_i3.add_paragraph() if tf_i3.paragraphs[0].text else tf_i3.paragraphs[0]
        p.text = f"■ {t}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_ACCENT_TEAL
        p2 = tf_i3.add_paragraph()
        p2.text = d
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(8)

    # =========================================================================
    # SLIDE 5: Master Data Persistence & Storage Matrix
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_ms_header(s5, "Enterprise Data Persistence & Storage Architecture", "DATA RETENTION & STORAGE MATRIX", 
                  "Comprehensive mapping of Relational, Vector, Object, and In-Memory storage layers")

    # Table representation of Storage Matrix
    table_shape = s5.shapes.add_table(6, 4, Inches(0.8), Inches(1.5), Inches(11.733), Inches(4.2))
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(2.8)
    table.columns[2].width = Inches(4.733)
    table.columns[3].width = Inches(2.0)

    headers = ["Storage Layer", "Target Resource / DB", "Data Types & Schema Stored", "Retention / Isolation"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_NAVY_DARK
        p = cell.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.LEFT

    rows_data = [
        ("Relational Database", "PostgreSQL Flexible Server\n(`psql-entchat-poc-sand`)", 
         "• Database `open_webui`: Users, Auth Sessions, Chat Histories, Prompts, Tools.\n• Database `litellm`: Token Usage, Spend Logs, Model Costs, API Keys.\n• Database `docwise`: Document processing state & task metadata.", 
         "Private Endpoint\nStrict DB Isolation"),
        ("Vector Search Store", "Azure AI Search\n(`srch-entchat-poc-sand`)", 
         "• `owui-knowledge`: Shared Knowledge Base embeddings.\n• `owui-files`: Chat attachments embeddings.\n• `owui-memory`: User personal memory embeddings.\n• `enterprise-docs-idx`: Master enterprise documents.\n• `docwise-docs-v2`: DocWise extracted document chunks.", 
         "Namespace Mode\n(Server-side OData Filter via `collection_key`)"),
        ("Object Storage", "Azure Blob Storage\n(`staentchatdoc`)", 
         "• `open-webui-files`: User file uploads.\n• `documents`: Enterprise source documents (PDF/DOCX).\n• `cost-reports`: Daily LiteLLM cost exports.", 
         "Hot Tier LRS\nPrivate Access"),
        ("In-Memory Cache", "LiteLLM Local Cache\n(In-Container Memory)", 
         "Exact Match Prompt & Response cache for identical LLM requests.\n• TTL: 3,600 seconds (1 hour).", 
         "Volatile / Auto-Evict\n(90% Cost Reduction)"),
        ("Local App Storage", "App Service Local Storage\n(`/app/backend/data`)", 
         "Ephemeral container cache, Nginx logs, and temporary conversion buffers.", 
         "Ephemeral Container")
    ]

    for row_idx, data in enumerate(rows_data, start=1):
        bg = COLOR_WHITE if row_idx % 2 == 1 else COLOR_CARD_ALT
        for col_idx, text in enumerate(data):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.color.rgb = COLOR_SLATE_DARK
            if col_idx == 0:
                p.font.bold = True
                p.font.color.rgb = COLOR_NAVY_DARK

    # Bottom note on Namespace Consolidation
    note_box = add_card(s5, Inches(0.8), Inches(5.9), Inches(11.733), Inches(1.15), "Architecture Highlight: Azure AI Search Namespace Consolidation", COLOR_AZURE_BLUE, COLOR_TAG_BG, COLOR_AZURE_BLUE)
    nt_tb = s5.shapes.add_textbox(Inches(0.95), Inches(6.25), Inches(11.4), Inches(0.7))
    tf_nt = nt_tb.text_frame
    tf_nt.word_wrap = True
    tf_nt.margin_left = tf_nt.margin_top = tf_nt.margin_right = tf_nt.margin_bottom = 0
    p_nt = tf_nt.paragraphs[0]
    p_nt.text = "Standard Azure AI Search has a hard limit of 200 indexes per service tier. To prevent quota exhaustion from dynamic user Knowledge Bases, our custom client consolidates all KBs into 3 shared indexes (`owui-knowledge`, `owui-files`, `owui-memory`) and enforces tenant isolation using server-side OData filtering on `collection_key`."
    p_nt.font.size = Pt(9.5)
    p_nt.font.color.rgb = COLOR_TAG_TEXT

    # =========================================================================
    # SLIDE 6: Architectural Tradeoffs, Cost & Operational Excellence
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_ms_header(s6, "Architectural Tradeoffs, Cost & Operational Excellence", "DECISION MATRIX & OPERATIONS", 
                  "Evaluation of core architectural decisions, monthly infrastructure costs, and deployment hygiene")

    col_w6 = Inches(5.7)
    gap6 = Inches(0.33)

    # Left: Architectural Tradeoffs
    add_card(s6, Inches(0.8), Inches(1.5), col_w6, Inches(5.6), "Architectural Tradeoffs Matrix", COLOR_NAVY_DARK)
    tb_t = s6.shapes.add_textbox(Inches(0.95), Inches(2.05), col_w6 - Inches(0.3), Inches(4.9))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0

    tradeoffs = [
        ("Azure AI Search vs ChromaDB", 
         "• Decision: Custom `AzureAISearchClient` over default local ChromaDB.\n• Rationale: Enterprise-grade hybrid search, native Azure VNet security, high availability, and persistent cloud vector management."),
        ("Namespace Consolidation vs 1-Index-Per-KB", 
         "• Decision: Shared index with `collection_key` server-side filtering.\n• Rationale: Avoids Standard Tier 200-index limit while maintaining multi-tenant data isolation."),
        ("LiteLLM Gateway vs Direct AI Foundry Access", 
         "• Decision: Centralized LiteLLM proxy with local caching.\n• Rationale: Enforces cross-app token quotas, unified spending dashboards, and prompt caching (90% savings on cache hits)."),
        ("Strict VNet Lockdown vs Open Outbound", 
         "• Decision: Block all outbound internet except Entra ID login tag.\n• Rationale: Zero data leakage policy; pre-downloading dependencies at build time.")
    ]
    for title, desc in tradeoffs:
        p = tf_t.add_paragraph() if tf_t.paragraphs[0].text else tf_t.paragraphs[0]
        p.text = f"■ {title}"
        p.font.bold = True
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_AZURE_BLUE
        p2 = tf_t.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(6)

    # Right: Monthly Cost & Operational Checklist
    add_card(s6, Inches(0.8) + col_w6 + gap6, Inches(1.5), col_w6, Inches(5.6), "Cost Model & Operational Best Practices", COLOR_AZURE_BLUE)
    tb_ops = s6.shapes.add_textbox(Inches(0.8) + col_w6 + gap6 + Inches(0.15), Inches(2.05), col_w6 - Inches(0.3), Inches(4.9))
    tf_ops = tb_ops.text_frame
    tf_ops.word_wrap = True
    tf_ops.margin_left = tf_ops.margin_top = tf_ops.margin_right = tf_ops.margin_bottom = 0

    cost_and_ops = [
        ("Monthly Estimated Infrastructure Cost (~$290 - $310 / mo)", 
         "• Azure AI Search (Standard Tier): ~$245 / mo\n• App Service Plan B2 Linux (Shared for OWUI & LiteLLM): ~$25 - $33 / mo\n• Azure PostgreSQL Flexible Server B1ms: ~$12 / mo\n• Storage, Private Endpoints, DNS: < $5 / mo\n• Model Inference: Pay-as-you-go via AI Foundry (discounted by LiteLLM cache)."),
        ("Production Deployment Hygiene (Rules of Thumb)", 
         "• AMD64 Architecture: App Service is Linux/AMD64; always build via `docker buildx --platform linux/amd64`.\n• Database Protection: Never share `.env` files between services to prevent LiteLLM Prisma migrations from modifying OWUI tables.\n• Startup Timeout: `WEBSITES_CONTAINER_START_TIME_LIMIT=1800` configured for large image initialization.")
    ]
    for title, desc in cost_and_ops:
        p = tf_ops.add_paragraph() if tf_ops.paragraphs[0].text else tf_ops.paragraphs[0]
        p.text = f"■ {title}"
        p.font.bold = True
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_NAVY_DARK
        p2 = tf_ops.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9)
        p2.font.color.rgb = COLOR_SLATE_DARK
        p2.space_after = Pt(8)

    prs.save(output_path)
    print(f"Presentation created successfully at: {output_path}")

if __name__ == "__main__":
    out = "haadthip_enterprise_ai_architecture.pptx"
    create_deck(out)
