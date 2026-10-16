"""Minimal, image-free Streamlit presentation primitives for AI Job Finder.

The ranking engine, source checks, and employer provenance remain untouched.
All dynamic strings are HTML-escaped before insertion into a Streamlit
markdown block. The layout is real Streamlit controls, not a fake dashboard.
"""
from html import escape

PALETTE={
    "background":"#27342F","panel":"#34443D","raised":"#3C4E45",
    "border":"#50655A","text":"#F1F6F2","muted":"#BBCDC2",
    "accent":"#257B5B","accent_dark":"#1B654A"
}

# Single source of truth for the compact slate-and-forest theme.
# No layered light-theme overrides, rounded bubbles, or green card borders.
# Dark gray-green ≠ black; every form/card remains a native Streamlit widget.
APP_CSS=r"""
<style>
:root{
  --page:#27342F;--paper:#34443D;--raised:#3C4E45;
  --ink:#F1F6F2;--muted:#BBCDC2;--forest:#257B5B;
  --forest-hover:#1B654A;--quiet:#3A4B43;
  --divider:#50655A;
}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],
[data-testid="stMain"],[data-testid="stMainBlockContainer"],
[data-testid="stHeader"]{
  background:var(--page)!important;
  color:var(--ink)!important;
}
[data-testid="stDecoration"]{display:none!important;}
[data-testid="stSidebar"],[data-testid="stSidebarNav"],
[data-testid="collapsedControl"]{display:none!important;}
/* One content gutter for every page. Never pad Streamlit's root
   VerticalBlock: it behaves differently inside page containers and columns.
   This fixes the uneven rails introduced in v3.1.19. */
[data-testid="stMainBlockContainer"],.block-container,
[data-testid="stMain"] .block-container{
  box-sizing:border-box!important;
  width:calc(100% - 6rem)!important;
  max-width:1440px!important;
  margin-inline:auto!important;
  padding:1.8rem clamp(24px,3vw,48px) 3.5rem!important;
  background:var(--page)!important;
  border:0!important;border-radius:0!important;
}
/* Dashboard already has its own internal module inset; leave that
   working layout's effective padding and content width intact. */
[data-testid="stMainBlockContainer"]:has(.st-key-dashboard_content),
.block-container:has(.st-key-dashboard_content){
  width:calc(100% - 5rem)!important;
  padding:1.65rem 1.25rem 3.5rem!important;
}
[data-testid="stForm"]{margin-top:.3rem!important;}

/* A real dashboard wrapper creates a second modest inset. Do not style
   it as one large rounded card; the six individual metrics are modules. */
.st-key-dashboard_content,
.st-key-dashboard_content[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--page)!important;
  padding:1rem 1.55rem 1.8rem!important;
  margin:0 auto!important;border:0!important;border-radius:0!important;
  box-shadow:none!important;
}
.st-key-dashboard_content > div[data-testid="stVerticalBlock"]{
  background:transparent!important;
  padding:.45rem .55rem 1rem!important;
  row-gap:1.3rem!important;
}
.st-key-dashboard_content [data-testid="stHorizontalBlock"]{
  column-gap:1.35rem!important;
  row-gap:1.35rem!important;
}
h1,h2,h3,h4,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3{
  color:var(--ink)!important;letter-spacing:-.025em!important;
  line-height:1.23!important;
}
h1{font-size:1.65rem!important;font-weight:750!important;}
h2{font-size:1.22rem!important;font-weight:710!important;}
h3{font-size:1.02rem!important;font-weight:690!important;}
p,li,[data-testid="stMarkdownContainer"]{
  color:var(--ink)!important;line-height:1.47!important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"] p{
  color:var(--muted)!important;font-size:.79rem!important;
}
hr{border-color:var(--divider)!important;margin:1rem 0!important;}

/* Compact top bar: independent tabs, not a surrounding capsule. */
.job-topbar{
  display:flex;align-items:center;justify-content:space-between;
  gap:.65rem;padding:.05rem 0 .65rem;margin:0 0 .45rem;
  border:0!important;
}
.job-brand{display:flex;align-items:center;gap:9px;}
.job-mark{
  width:23px;height:23px;border-radius:3px;
  background:var(--forest);display:inline-block;
  position:relative;flex:none;
}
.job-mark:after{
  content:"";position:absolute;left:8px;top:5px;
  width:7px;height:12px;border-left:2px solid white;
  border-bottom:2px solid white;transform:rotate(-40deg);
}
.job-brand-title{
  font-size:1.01rem;font-weight:760;letter-spacing:-.02em;
  color:var(--ink)!important;
}
.job-version{
  font-size:.72rem;color:var(--muted)!important;
  font-weight:550;white-space:nowrap;
}
.st-key-top_navigation [data-testid="stWidgetLabel"]{display:none!important;}
.st-key-top_navigation [role="radiogroup"]{
  display:flex!important;flex-wrap:wrap!important;gap:5px!important;
  padding:0!important;border:0!important;background:transparent!important;
  border-radius:0!important;box-shadow:none!important;
}
.st-key-top_navigation [role="radiogroup"] label{
  margin:0!important;padding:9px 15px!important;min-height:40px!important;
  background:var(--paper)!important;border:0!important;
  border-radius:3px!important;cursor:pointer;
}
.st-key-top_navigation [role="radiogroup"] label>div:first-child{display:none!important;}
.st-key-top_navigation [role="radiogroup"] label:hover{
  background:var(--raised)!important;
}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked){
  background:var(--forest)!important;
}
.st-key-top_navigation [role="radiogroup"] label p{
  font-size:.84rem!important;color:var(--ink)!important;
  font-weight:600!important;line-height:1.1!important;
}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) *,
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) p{
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}

/* Clear modular headings outside the panels, not heavy bordered wrappers. */
.job-hero{padding:.65rem 0 .55rem!important;margin:0 0 .25rem!important;}
.job-hero h1{margin:.1rem 0 .22rem!important;}
.job-section-kicker{
  font-size:.65rem;letter-spacing:.09em;font-weight:750;
  text-transform:uppercase;color:#82CEAA!important;margin-bottom:5px;
}
.job-subline{font-size:.80rem;color:var(--muted)!important;line-height:1.4;}
.job-module-heading{
  margin:1.6rem 0 .72rem!important;padding:0!important;
  border:0!important;color:var(--ink)!important;
  font-size:1.02rem;font-weight:735;letter-spacing:-.012em;
}
.job-module-caption{
  color:var(--muted)!important;font-size:.78rem;
  line-height:1.4;margin:-.15rem 0 .8rem;
}

/* Compact independent modules: separation through contrasting surfaces
   and narrow gutters, never colored borders or large rounded outlines. */
[data-testid="stForm"],
[data-testid="stMetric"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"],
[data-testid="stDataFrame"]{
  background:var(--paper)!important;
  border:0!important;border-radius:4px!important;
  box-shadow:0 2px 10px rgba(12,22,18,.13)!important;
}
[data-testid="stForm"]{
  padding:1.45rem 1.65rem!important;
}
/* Inset panels inside the outer page gutter, not flush with its edge. */
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"]:not(.st-key-dashboard_content){
  box-sizing:border-box!important;
  width:calc(100% - 32px)!important;
  margin-left:16px!important;margin-right:16px!important;
}
[data-testid="stForm"]{padding:1.3rem 1.5rem!important;}
.job-hero,.job-module-heading,.job-module-caption,.job-topbar,
.st-key-top_navigation{margin-left:16px!important;margin-right:16px!important;}
.st-key-dashboard_content .job-hero,
.st-key-dashboard_content .job-module-heading{margin-left:0!important;margin-right:0!important;}
[data-testid="stVerticalBlockBorderWrapper"]{
  margin-bottom:14px!important;
}
[data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
  background:transparent!important;border:0!important;
  padding:1.18rem 1.38rem!important;
  border-radius:4px!important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"]{
  row-gap:.72rem!important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p{
  margin:.15rem 0 .34rem!important;line-height:1.47!important;
}
[data-testid="stMetric"]{
  padding:1.12rem 1.32rem!important;
  min-height:105px!important;
}
[data-testid="stMetricLabel"] p{
  color:var(--muted)!important;font-size:.73rem!important;
}
[data-testid="stMetricValue"]{
  color:var(--ink)!important;
  font-size:1.62rem!important;font-weight:745!important;
}
[data-testid="stExpander"] summary{
  padding:10px 14px!important;min-height:41px!important;
  color:var(--ink)!important;
}
[data-testid="stExpander"] summary *{
  color:var(--ink)!important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"]{
  padding:.85rem 1.15rem 1.1rem!important;
}
[data-testid="stTabs"] button{
  color:var(--muted)!important;font-size:.79rem;font-weight:625;
}
[data-testid="stDataFrame"]{overflow:hidden;}

/* Streamlit native input controls: smaller but readable, no green outline. */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"]>div>div,
[data-testid="stMultiSelect"]>div>div,
[data-testid="stDateInput"] input{
  background:var(--raised)!important;
  color:var(--ink)!important;
  border:0!important;border-radius:3px!important;
  min-height:40px!important;
  font-size:.86rem!important;
}
input::placeholder,textarea::placeholder{
  color:var(--muted)!important;opacity:1!important;
}
.stButton button,[data-testid="stDownloadButton"] button,
[data-testid="stLinkButton"] a,[data-testid="stFormSubmitButton"] button{
  border:0!important;border-radius:3px!important;
  min-height:40px!important;padding:9px 15px!important;
  background:var(--raised)!important;
  color:var(--ink)!important;font-size:.85rem!important;
  font-weight:650!important;
}
.stButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button{
  background:var(--forest)!important;color:#FFFFFF!important;
}
.stButton button[kind="primary"] *,
[data-testid="stFormSubmitButton"] button[kind="primary"] *,
[data-testid="stDownloadButton"] button *,
.stButton button[kind="primary"] p,
[data-testid="stFormSubmitButton"] button[kind="primary"] p,
[data-testid="stDownloadButton"] button p{
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
.stButton button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
[data-testid="stDownloadButton"] button:hover{
  background:var(--forest-hover)!important;
}
.stButton button[kind="primary"]:hover *,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover *,
[data-testid="stDownloadButton"] button:hover *{
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
button:focus-visible,input:focus-visible,textarea:focus-visible{
  outline:2px solid #8DD4B2!important;outline-offset:2px!important;
}
/* Uncolored pill shapes, minimal metadata rows and smaller score readout. */
.job-card-top{margin:0 0 7px;}
 .job-role{font-size:1.10rem;font-weight:730;line-height:1.35;color:var(--ink)!important;}
.job-meta{font-size:.83rem;line-height:1.38;color:var(--muted)!important;margin-top:5px;}
.job-tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px;}
.job-pill{
  display:inline-flex;align-items:center;line-height:1.25;
  font-size:.71rem;font-weight:610;letter-spacing:0;
  color:var(--ink)!important;background:var(--raised);
  padding:5px 8px;border:0!important;border-radius:2px;
}
.job-pill.mint{
  background:var(--forest)!important;color:#FFFFFF!important;
}
.job-pill.warn{background:#63533B;color:#F6DEAD!important;}
.job-pill.blue{background:#3C5660;color:#D7EFF5!important;}
.job-score{
  font-size:1.67rem;font-weight:745;
  color:#9FE3BC!important;letter-spacing:-.035em;
  line-height:1.17;margin-top:6px;
}
.job-score-denom{font-size:.73rem;color:var(--muted)!important;font-weight:520;}
.job-small{
  color:var(--muted)!important;font-size:.69rem;
  letter-spacing:.04em;text-transform:uppercase;font-weight:620;
}
.job-hint{font-size:.74rem;color:var(--muted)!important;}

@media(max-width:900px){
  [data-testid="stMainBlockContainer"],.block-container,
  [data-testid="stMain"] .block-container{
    width:100%!important;max-width:100%!important;
    padding:1rem 1.2rem 3rem!important;
  }
  .st-key-dashboard_content{padding:.55rem .6rem 1.15rem!important;}
  .st-key-dashboard_content > div[data-testid="stVerticalBlock"]{
    padding:.2rem .15rem .7rem!important;
  }
  .job-topbar{flex-wrap:wrap!important;}
  .st-key-top_navigation [role="radiogroup"]{gap:4px!important;}
  .st-key-top_navigation [role="radiogroup"] label{
    padding:7px 9px!important;min-height:33px!important;
  }
  [data-testid="stForm"]{padding:1rem 1.1rem!important;}
  [data-testid="stMetric"]{padding:.9rem 1rem!important;min-height:92px!important;}
  [data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
    padding:.98rem 1.08rem!important;
  }
  h1{font-size:1.48rem!important;}
}
</style>
"""

def _safe(value):
    return escape(str(value if value is not None else ""),quote=True)


def brand(version=""):
    return ('<div class="job-topbar"><div class="job-brand">'
            '<span class="job-mark" aria-hidden="true"></span>'
            '<span class="job-brand-title">AI Job Finder</span></div>'
            + ('<span class="job-version">Version '+_safe(version)+' · Compact Slate</span>'
               if version else '') + '</div>')


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
