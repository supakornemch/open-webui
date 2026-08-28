from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

OUT = 'haadthip_enterprise_ai_architecture_visual.pptx'
W, H = 13.333, 7.5
C = {
    'bg': RGBColor(248, 249, 250), 'white': RGBColor(255,255,255),
    'navy': RGBColor(16,37,66), 'text': RGBColor(36,41,47),
    'muted': RGBColor(90,105,120), 'line': RGBColor(215,223,232),
    'blue': RGBColor(0,120,212), 'blue2': RGBColor(234,243,253),
    'teal': RGBColor(0,164,180), 'teal2': RGBColor(230,248,249),
    'green': RGBColor(16,124,65), 'green2': RGBColor(231,246,237),
    'orange': RGBColor(216,59,1), 'orange2': RGBColor(255,241,235),
    'purple': RGBColor(106,65,153), 'purple2': RGBColor(243,238,250),
}
prs = Presentation(); prs.slide_width=Inches(W); prs.slide_height=Inches(H)
blank = prs.slide_layouts[6]

def box(slide,x,y,w,h,fill='white',line='line',radius=True):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x),Inches(y),Inches(w),Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb=C[fill]; s.line.color.rgb=C[line]; s.line.width=Pt(1)
    return s

def text(slide,x,y,w,h,txt,size=12,color='text',bold=False,align=PP_ALIGN.LEFT,margin=.04):
    t=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=t.text_frame; tf.clear(); tf.word_wrap=True
    tf.margin_left=tf.margin_right=Inches(margin); tf.margin_top=tf.margin_bottom=Inches(margin); tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    p=tf.paragraphs[0]; p.text=txt; p.alignment=align; p.font.name='Aptos'; p.font.size=Pt(size); p.font.bold=bold; p.font.color.rgb=C[color]
    return t

def title(slide,kicker,heading,sub=''):
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb=C['bg']
    bar=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,Inches(W),Inches(.09)); bar.fill.solid(); bar.fill.fore_color.rgb=C['blue']; bar.line.fill.background()
    text(slide,.72,.32,11.8,.22,kicker.upper(),9,'blue',True)
    text(slide,.72,.57,11.9,.48,heading,22,'navy',True)
    if sub: text(slide,.72,1.08,11.8,.28,sub,10,'muted')
    line=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.72),Inches(1.42),Inches(11.9),Inches(.012)); line.fill.solid(); line.fill.fore_color.rgb=C['line']; line.line.fill.background()

def pill(slide,x,y,w,label,color='blue',fill=None):
    fill=fill or color+'2'
    box(slide,x,y,w,.3,fill,color)
    text(slide,x,y+.01,w,.26,label,8,color,True,PP_ALIGN.CENTER)

def node(slide,x,y,w,h,label,sub,color='blue',fill='white'):
    box(slide,x,y,w,h,fill,color)
    text(slide,x+.12,y+.10,w-.24,.28,label,11,color,True,PP_ALIGN.CENTER)
    text(slide,x+.12,y+.42,w-.24,h-.5,sub,8.5,'muted',False,PP_ALIGN.CENTER)

def arrow(slide,x1,y1,x2,y2,color='blue'):
    a=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2)); a.line.color.rgb=C[color]; a.line.width=Pt(2); a.line.end_arrowhead=True

def footer(slide,n):
    text(slide,.72,7.18,6,.18,'HAADTHIP  |  ENTERPRISE AI PLATFORM',7,'muted',True)
    text(slide,12.0,7.18,.6,.18,f'{n:02d}',8,'muted',True,PP_ALIGN.RIGHT)

# 1 cover
s=prs.slides.add_slide(blank); s.background.fill.solid(); s.background.fill.fore_color.rgb=C['bg']
bar=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,Inches(W),Inches(.12)); bar.fill.solid(); bar.fill.fore_color.rgb=C['blue']; bar.line.fill.background()
text(s,.9,.9,11.5,.25,'AZURE ARCHITECTURE REFERENCE',10,'blue',True)
text(s,.9,1.35,11.3,.8,'HaadThip Enterprise AI Platform',30,'navy',True)
text(s,.9,2.25,10.8,.45,'EnterpriseChat (Genie) + DocWise',17,'muted')
text(s,.9,2.95,10.5,.42,'Two systems. One governed Azure foundation.',13,'text')
# visual architecture motif
node(s,1.0,4.35,2.55,1.25,'GENIE','Conversational AI','blue','blue2')
node(s,5.38,4.35,2.55,1.25,'AZURE AI','Shared platform','teal','teal2')
node(s,9.76,4.35,2.55,1.25,'DOCWISE','Document intelligence','purple','purple2')
arrow(s,3.58,4.98,5.32,4.98,'blue'); arrow(s,7.95,4.98,9.7,4.98,'teal')
pill(s,5.7,3.78,1.9,'SHARED LANDING ZONE','blue')
footer(s,1)

# 2 landscape
s=prs.slides.add_slide(blank); title(s,'SYSTEM LANDSCAPE','Two products, shared Azure services','The apps are separate workloads; identity, AI, search, storage and network are shared capabilities.')
# clients
node(s,.85,2.1,2.0,1.0,'USERS','Teams / Browser','blue','blue2')
node(s,.85,4.65,2.0,1.0,'OPERATORS','Admin / Upload','purple','purple2')
# apps
node(s,3.65,2.0,2.25,1.2,'GENIE','Open WebUI + LiteLLM','blue','white')
node(s,3.65,4.55,2.25,1.2,'DOCWISE','Django document workflow','purple','white')
arrow(s,2.9,2.6,3.58,2.6); arrow(s,2.9,5.15,3.58,5.15)
# shared services
node(s,6.85,1.8,2.2,1.0,'ENTRA ID','OIDC / Teams SSO','orange','orange2')
node(s,6.85,3.25,2.2,1.0,'AI FOUNDRY','GPT + Embeddings','teal','teal2')
node(s,6.85,4.7,2.2,1.0,'AI SEARCH','Hybrid retrieval','teal','teal2')
node(s,10.0,2.55,2.2,1.0,'POSTGRESQL','App + usage state','green','green2')
node(s,10.0,4.0,2.2,1.0,'BLOB STORAGE','Raw documents','green','green2')
for y in (2.6,5.15): arrow(s,5.98,y,6.77,3.75,'teal')
arrow(s,5.98,2.6,6.77,2.3,'orange'); arrow(s,5.98,5.15,6.77,5.2,'teal')
arrow(s,9.12,2.65,9.92,3.05,'green'); arrow(s,9.12,5.2,9.92,4.5,'green')
pill(s,6.95,6.15,1.95,'VNET INTEGRATED','navy', 'white'); footer(s,2)

# 3 landing zone
s=prs.slides.add_slide(blank); title(s,'LANDING ZONE','Security boundaries and network placement','Public entry points terminate at the workload boundary; data services remain private.')
# zone bands
box(s,.75,1.75,3.55,4.95,'blue2','blue',False); box(s,4.55,1.75,4.25,4.95,'white','navy',False); box(s,9.05,1.75,3.55,4.95,'teal2','teal',False)
text(s,.98,1.94,3.1,.3,'ZONE 1  |  INGRESS & IDENTITY',10,'blue',True,PP_ALIGN.CENTER)
text(s,4.78,1.94,3.8,.3,'ZONE 2  |  WORKLOAD VNET',10,'navy',True,PP_ALIGN.CENTER)
text(s,9.28,1.94,3.1,.3,'ZONE 3  |  DATA & AI',10,'teal',True,PP_ALIGN.CENTER)
node(s,1.15,2.55,2.75,.85,'TEAMS / BROWSER','HTTPS entry','blue','white'); node(s,1.15,4.0,2.75,.85,'ENTRA ID','OIDC / MFA','orange','orange2'); node(s,1.15,5.45,2.75,.85,'CUSTOM DOMAIN','genie.haadthip.com','blue','white')
node(s,5.0,2.55,3.35,.85,'OPEN WEBUI','Chat + RAG orchestration','blue','blue2'); node(s,5.0,4.0,3.35,.85,'LITELLM','Gateway + cache + MCP','navy','white'); node(s,5.0,5.45,3.35,.85,'DOCWISE APP','Django workflow','purple','purple2')
node(s,9.45,2.55,2.75,.85,'AI FOUNDRY','GPT + embedding','teal','white'); node(s,9.45,4.0,2.75,.85,'AI SEARCH','Private endpoint','teal','white'); node(s,9.45,5.45,2.75,.85,'POSTGRES + BLOB','State + source files','green','green2')
arrow(s,3.95,2.98,4.9,2.98); arrow(s,3.95,4.43,4.9,4.43); arrow(s,8.45,2.98,9.35,2.98,'teal'); arrow(s,8.45,4.43,9.35,4.43,'teal'); arrow(s,8.45,5.88,9.35,5.88,'green')
text(s,4.9,6.55,3.6,.2,'NSG: outbound blocked by default',8,'orange',True,PP_ALIGN.CENTER); footer(s,3)

# 4 Genie flow
s=prs.slides.add_slide(blank); title(s,'GENIE','Conversational request flow','A single user prompt moves through identity, retrieval, gateway policy and model inference.')
# swimlane visual
steps=[('1','USER','Prompt','blue','blue2'),('2','OPEN WEBUI','Build context','blue','white'),('3','AI SEARCH','Hybrid retrieve','teal','teal2'),('4','LITELLM','Cache / route','navy','white'),('5','AI FOUNDRY','Generate','teal','teal2'),('6','USER','Stream answer','green','green2')]
xs=[.75,2.75,4.75,6.75,8.75,10.75]
for i,(num,lbl,sub,col,fill) in enumerate(steps):
    box(s,xs[i],2.4,1.65,1.55,fill,col); pill(s,xs[i]+.57,2.58,.5,num,col,fill); text(s,xs[i]+.12,3.0,1.41,.25,lbl,10,col,True,PP_ALIGN.CENTER); text(s,xs[i]+.12,3.35,1.41,.35,sub,9,'muted',False,PP_ALIGN.CENTER)
    if i<5: arrow(s,xs[i]+1.68,3.18,xs[i+1]-.07,3.18,col)
# side detail
box(s,.95,4.55,3.55,1.35,'white','line'); text(s,1.15,4.72,3.1,.25,'AUTHENTICATION',10,'orange',True); text(s,1.15,5.08,3.1,.55,'Teams SDK popup -> Entra ID -> token cookie -> session',10,'text')
box(s,4.9,4.55,3.55,1.35,'white','line'); text(s,5.1,4.72,3.1,.25,'RAG RETRIEVAL',10,'teal',True); text(s,5.1,5.08,3.1,.55,'Embedding 3072d + HNSW + BM25 + collection_key filter',10,'text')
box(s,8.85,4.55,3.55,1.35,'white','line'); text(s,9.05,4.72,3.1,.25,'GOVERNANCE',10,'navy',True); text(s,9.05,5.08,3.1,.55,'LiteLLM cache, token usage, cost and model policy',10,'text')
footer(s,4)

# 5 DocWise flow
s=prs.slides.add_slide(blank); title(s,'DOCWISE','Document intelligence pipeline','Raw files become searchable knowledge through extraction, chunking, embedding and indexing.')
steps=[('SOURCE','PDF / DOCX / MD','green','green2'),('EXTRACT','Document Intelligence\nprebuilt-read','orange','orange2'),('CHUNK','1000 / 100\nrecursive splitter','blue','blue2'),('EMBED','text-embedding-3-large\n3072 dimensions','teal','teal2'),('INDEX','docwise-docs-v2\nHNSW vectors','purple','purple2')]
xs=[.8,3.25,5.7,8.15,10.6]
for i,(lbl,sub,col,fill) in enumerate(steps):
    node(s,xs[i],2.55,1.9,1.35,lbl,sub,col,fill)
    if i<4: arrow(s,xs[i]+1.93,3.23,xs[i+1]-.08,3.23,col)
# output fanout
text(s,.9,4.65,11.2,.25,'OUTPUTS',10,'muted',True,PP_ALIGN.CENTER)
node(s,1.4,5.2,2.65,.85,'SEARCHABLE DOCS','AI Search index','teal','teal2'); node(s,5.35,5.2,2.65,.85,'SUMMARY / METADATA','DocWise DB','green','green2'); node(s,9.3,5.2,2.65,.85,'GENIE RAG','Enterprise retrieval','blue','blue2')
arrow(s,6.65,3.98,2.72,5.12,'teal'); arrow(s,6.65,3.98,6.67,5.12,'green'); arrow(s,6.65,3.98,10.62,5.12,'blue'); footer(s,5)

# 6 storage
s=prs.slides.add_slide(blank); title(s,'DATA','Where information lives','Each storage service owns a distinct data class; vector data and source files are deliberately separated.')
# central source to stores
node(s,.9,3.0,2.1,1.0,'APPS','Genie + DocWise','blue','blue2')
node(s,4.0,1.85,2.4,1.0,'POSTGRESQL','Users / chats / usage','green','green2')
node(s,4.0,3.2,2.4,1.0,'AI SEARCH','Chunks / vectors / metadata','teal','teal2')
node(s,4.0,4.55,2.4,1.0,'BLOB STORAGE','Original files / uploads','green','green2')
node(s,8.0,2.15,2.4,1.0,'OWUI KNOWLEDGE','Shared KBs','blue','blue2')
node(s,8.0,3.5,2.4,1.0,'ENTERPRISE DOCS','Master corpus','teal','teal2')
node(s,8.0,4.85,2.4,1.0,'DOCWISE DOCS','Document index','purple','purple2')
arrow(s,3.05,3.5,3.92,2.35,'green'); arrow(s,3.05,3.5,3.92,3.7,'teal'); arrow(s,3.05,3.5,3.92,5.05,'green')
arrow(s,6.48,3.7,7.92,2.65,'blue'); arrow(s,6.48,3.7,7.92,4.0,'teal'); arrow(s,6.48,3.7,7.92,5.35,'purple')
# footer callouts
pill(s,10.75,2.28,1.55,'PRIVATE ENDPOINT','teal'); pill(s,10.75,3.63,1.55,'NAMESPACE KEY','blue'); pill(s,10.75,4.98,1.55,'HNSW INDEX','purple')
text(s,1.0,6.35,11.3,.32,'LiteLLM local cache: volatile, TTL 3600s, reduces repeated model cost.',10,'navy',True,PP_ALIGN.CENTER); footer(s,6)

# 7 decisions
s=prs.slides.add_slide(blank); title(s,'ARCHITECTURE DECISIONS','The principles behind the design','A concise decision record for reviewers and implementation teams.')
items=[('PRIVATE BY DEFAULT','PostgreSQL and AI Search are not public. Workloads reach them through VNet / private access.','orange','orange2'),('CENTRAL AI GATEWAY','LiteLLM is the control point for model routing, caching, spend and usage.','navy','white'),('SEARCH AS A PLATFORM','Azure AI Search provides one managed retrieval layer for Genie and DocWise.','teal','teal2'),('SOURCE IS NOT VECTOR','Blob keeps the original document; Search keeps derived chunks and embeddings.','green','green2'),('SHARED INDEX, ISOLATED DATA','Namespace consolidation avoids index limits while collection_key enforces boundaries.','blue','blue2'),('BUILD FOR AZURE','AMD64 images, baked dependencies and explicit DB ownership support reliable deployment.','purple','purple2')]
coords=[(.9,1.9),(4.55,1.9),(8.2,1.9),(.9,4.25),(4.55,4.25),(8.2,4.25)]
for (head,desc,col,fill),(x,y) in zip(items,coords):
    box(s,x,y,3.25,1.55,fill,col); text(s,x+.16,y+.18,2.93,.3,head,10,col,True,PP_ALIGN.CENTER); text(s,x+.22,y+.62,2.81,.65,desc,9,'text',False,PP_ALIGN.CENTER)
footer(s,7)

prs.save(OUT); print(OUT)
