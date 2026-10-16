"""Minimal, image-free Streamlit presentation primitives for AI Job Finder.

The ranking engine, source checks, and employer provenance remain untouched.
All dynamic strings are HTML-escaped before insertion into a Streamlit
markdown block. The layout is real Streamlit controls, not a fake dashboard.
"""
from html import escape

PALETTE={
    "background":"#0B1114","panel":"#111B1F","raised":"#182428",
    "border":"#29393A","text":"#EAF5F1","muted":"#99ADA9",
    "accent":"#6FDCC2","accent_dark":"#194A3E"
}

APP_CSS=r"""
<style>
:root {
  --ink: #EAF5F1; --muted: #9DAFAC; --accent:#70DDC3;
  --panel:#121C20; --panel-alt:#182429; --border:#29393C;
}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"] {
    background: #0B1114; color: var(--ink);
}
[data-testid="stHeader"] { background:transparent!important; }
[data-testid="stDecoration"] { display:none; }
[data-testid="stSidebar"] {background: #10191D!important;
  border-right:1px solid #283639;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding:26px 20px 20px;
}
[data-testid="stSidebar"] .stRadio>label {display:none;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:7px;}
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius:12px;padding:10px 13px;margin:0;
  background:transparent;transition:background .14s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
  background:#1A2B2D;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background:linear-gradient(120deg,#193B35,#15332E);
  color:#B0F7E4;
}
[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
  font-size:.94rem; font-weight:550;
}
[data-testid="block-container"] {max-width:1480px;
  padding-top:2rem;padding-bottom:5rem;padding-left:2.3rem;padding-right:2.3rem;}
h1,h2,h3 {letter-spacing:-.035em!important;line-height:1.2!important;}
h1 {font-size:2rem!important;font-weight:750!important;margin-bottom:.45rem!important;}
h2 {font-size:1.35rem!important;font-weight:700!important;}
h3 {font-size:1.04rem!important;font-weight:700!important;}
p,li {line-height:1.5;}
[data-testid="stCaptionContainer"] {color:#92A5A2!important;}
[data-testid="stMetric"] {
  background:linear-gradient(145deg,#182824,#121D20);
  border:1px solid #2B4140;
  border-radius:16px;padding:21px 23px;
  min-height:108px;
}
[data-testid="stMetricLabel"] p {font-size:.81rem!important;color:#B0C3BD!important;
  letter-spacing:.02em;}
[data-testid="stMetricValue"] {font-size:1.9rem!important;
  font-weight:720!important; color:#EAF9F3!important;}
[data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"] {
  background:linear-gradient(135deg,#151F24 0%,#121B1F 100%);
  border-radius:15px;padding:13px 17px; }
[data-testid="stVerticalBlockBorderWrapper"] {
  border:1px solid #27373B!important;border-radius:17px!important;
  box-shadow:0 5px 24px rgba(0,0,0,.09);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color:#436961!important;
}
.stButton button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{
  color:#08271F!important;background:#71D8BB!important;border:1px solid #71D8BB!important;
  font-weight:750;border-radius:12px;min-height:43px;}
.stButton button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
 background:#95F0D5!important;border-color:#95F0D5!important;}
.stButton button,[data-testid="stDownloadButton"] button,
[data-testid="stLinkButton"] a {border-radius:11px!important;min-height:38px;}
[data-testid="stForm"] {
 background:linear-gradient(155deg,#131F22,#10191D);
 border:1px solid #26373B;border-radius:18px;padding:20px 22px;
}
[data-testid="stTextInput"] input, [data-testid="stSelectbox"]>div>div,
[data-testid="stNumberInput"] input {
  border-radius:10px!important;background:#121C21!important;
}
[data-testid="stExpander"] {border:1px solid #2B3B3D!important;
 border-radius:12px!important;background:#121B1E;}
[data-testid="stExpander"] summary {min-height:44px;}
[data-testid="stTabs"] button {font-weight:600;}
[data-testid="stDataFrame"] {border:1px solid #2D3E42;border-radius:12px;}
.job-brand {display:flex;align-items:center;gap:9px;margin:0 0 23px;}
.job-mark {width:23px;height:23px;border-radius:7px;
  background:linear-gradient(135deg,#9AF6DA,#246F5D);
  display:inline-block;clip-path:polygon(50% 0%,100% 88%,74% 100%,48% 48%,26% 100%,0 88%);}
.job-brand-title {font-size:1.23rem;font-weight:760;letter-spacing:-.025em;color:#EAF6F1}
.job-section-kicker {font-size:.72rem;text-transform:uppercase;
  letter-spacing:.125em;color:#75B7A7;font-weight:750;margin-bottom:7px;}
.job-hero {padding:3px 0 19px;}
.job-hero h1{margin:.12rem 0 .35rem!important;}
.job-subline{color:#9CACAA;font-size:.91rem;line-height:1.4;}
.job-card-top{margin:0 0 9px 0;}
.job-role{font-size:1.16rem;font-weight:740;line-height:1.3;color:#EFF7F3;}
.job-meta{font-size:.89rem;color:#A9B8B6;margin-top:5px;}
.job-tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px;}
.job-pill{display:inline-block;font-size:.73rem;letter-spacing:.005em;
  font-weight:600;color:#C2D4D0;background:#223036;padding:4px 9px;
  border:1px solid #314248;border-radius:30px;}
.job-pill.mint{background:#194135;color:#9CE8D2;border-color:#285B4D;}
.job-pill.warn{background:#443727;color:#F0D59C;border-color:#62503B;}
.job-pill.blue{background:#203549;color:#ADD5FF;border-color:#35526E;}
.job-score{font-size:2rem;font-weight:750;color:#8FE8D3;
  letter-spacing:-.05em;line-height:1.08;margin-top:4px;}
.job-score-denom{font-size:.81rem;color:#91ABA5;font-weight:550;}
.job-small{color:#89A6A0;font-size:.75rem;letter-spacing:.04em;text-transform:uppercase}
.job-hint{font-size:.8rem;color:#7F9794;}
hr {border-color:#29393B;}
@media(max-width:850px){
 [data-testid="block-container"]{padding-left:1.1rem;padding-right:1.1rem;padding-top:1rem;}
 h1{font-size:1.65rem!important;}
}
</style>
"""


def _safe(value):
    return escape(str(value if value is not None else ""),quote=True)


def brand():
    return ('<div class="job-brand"><span class="job-mark" aria-hidden="true"></span>'
            '<span class="job-brand-title">AI Job Finder</span></div>')


def hero(title,subtitle=""):
    # The same small typographic hierarchy on Dashboard, Search and Tracker.
    return ('<div class="job-hero"><div class="job-section-kicker">CAREER INTELLIGENCE</div>'
            '<h1>'+_safe(title)+'</h1>'+
            ('<div class="job-subline">'+_safe(subtitle)+'</div>' if subtitle else '')+
            '</div>')


def pill(label,tone="neutral"):
    tone=tone if tone in ("mint","warn","blue") else ""
    return '<span class="job-pill '+tone+'">'+_safe(label)+'</span>'


def listing_head(title,company,location,work_style,government,score=None,
                 is_new=False,restricted=False,verify=False,degree=False,
                 relocation=False,direct=True):
    tags=[pill("Government" if government else "Private"),
          pill(work_style or "Unspecified")]
    if is_new:tags.append(pill("New","mint"))
    if restricted:tags.append(pill("Internal only","warn"))
    elif verify:tags.append(pill("Verify requirements","warn"))
    elif degree:tags.append(pill("Degree check","blue"))
    if relocation:tags.append(pill("Relocation OK","blue"))
    if direct:tags.append(pill("Direct employer","mint"))
    score_html=(' <div class="job-small">FIT INDEX</div>'
                '<div class="job-score">'+_safe(score)+
                '<span class="job-score-denom"> / 96</span></div>') if score is not None else ""
    return ('<div class="job-card-top"><div class="job-role">'+_safe(title)+'</div>'
            '<div class="job-meta">'+_safe(company)+' &nbsp;·&nbsp; '+_safe(location)+'</div>'
            '<div class="job-tags">'+''.join(tags)+'</div></div>'+score_html)


def mini_brand_tag():
    return '<div class="job-small">JOB SEARCH</div>'
