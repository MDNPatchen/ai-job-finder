"""Minimal, image-free Streamlit presentation primitives for AI Job Finder.

The ranking engine, source checks, and employer provenance remain untouched.
All dynamic strings are HTML-escaped before insertion into a Streamlit
markdown block. The layout is real Streamlit controls, not a fake dashboard.
"""
from html import escape

PALETTE={
    "background":"#F5F7F5","panel":"#FFFFFF","raised":"#F8FAF8",
    "border":"#DDE7E1","text":"#1D332D","muted":"#667970",
    "accent":"#146B54","accent_dark":"#0D513F"
}

# Intentionally plain, light, and image-free. The CSS improves native
# Streamlit layout instead of covering forms/buttons with fake HTML controls.
APP_CSS=r"""
<style>
:root{
  --page:#F5F7F5;--paper:#FFFFFF;--quiet:#F1F6F2;
  --ink:#1D332D;--muted:#63766E;--forest:#146B54;
  --border:#DCE6E0;--hover:#F4F9F5;
}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],
[data-testid="stMain"],[data-testid="stMainBlockContainer"]{
  background-color:var(--page)!important;color:var(--ink)!important;
}
[data-testid="stHeader"]{background-color:var(--page)!important;}
[data-testid="stDecoration"]{display:none;}
/* Navigation now lives in the main page rather than a collapsible left rail. */
[data-testid="stSidebar"],[data-testid="stSidebarNav"],
[data-testid="collapsedControl"]{display:none!important;}
[data-testid="block-container"]{
  max-width:1440px!important;
  padding:1.75rem 2.65rem 5rem!important;
}
h1,h2,h3{
  color:var(--ink)!important;letter-spacing:-.035em!important;
  line-height:1.26!important;
}
h1{font-size:2.05rem!important;font-weight:750!important;}
h2{font-size:1.38rem!important;font-weight:710!important;}
h3{font-size:1.08rem!important;font-weight:680!important;}
p,li{color:var(--ink);line-height:1.6!important;}
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"]{color:var(--muted)!important;}
hr{border-color:var(--border)!important;margin:1.45rem 0!important;}

/* Top bar: compact wordmark, comfortable segmented navigation tabs. */
.job-topbar{
  display:flex;align-items:center;justify-content:space-between;
  gap:1rem;padding:0.15rem 0 1.05rem;
  border-bottom:1px solid var(--border);margin-bottom:0.8rem;
}
.job-brand{display:flex;align-items:center;gap:11px;}
.job-mark{
  width:29px;height:29px;border-radius:9px;background:var(--forest);
  display:inline-block;position:relative;flex:none;
}
.job-mark:after{
  content:"";position:absolute;left:10px;top:7px;
  width:9px;height:15px;border-left:3px solid white;
  border-bottom:3px solid white;transform:rotate(-40deg);
}
.job-brand-title{font-size:1.22rem;font-weight:780;
  letter-spacing:-.025em;color:#143E31;}
.job-version{font-size:.79rem;color:var(--muted);
  font-weight:550;white-space:nowrap;}
[data-testid="stRadio"]:has([data-testid="stWidgetLabel"] [aria-hidden="true"]) {}
.st-key-top_navigation [data-testid="stWidgetLabel"]{display:none!important;}
.st-key-top_navigation [role="radiogroup"]{
  display:flex!important;flex-wrap:wrap!important;gap:7px!important;
  padding:8px!important;border:1px solid var(--border)!important;
  background:var(--paper)!important;border-radius:15px!important;
  box-shadow:0 1px 4px rgba(24,56,39,.025);
}
.st-key-top_navigation [role="radiogroup"] label{
  margin:0!important;padding:10px 15px!important;
  border-radius:10px!important;min-height:42px;
  background:transparent;transition:background-color .12s ease;
  border:1px solid transparent;cursor:pointer;
}
.st-key-top_navigation [role="radiogroup"] label:hover{background:var(--hover);}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked){
  background:#E3F1E9!important;border-color:#B9DAC9!important;
}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) p{
  color:#105B45!important;font-weight:750!important;
}
.st-key-top_navigation [role="radiogroup"] label p{
  font-size:.90rem!important;font-weight:590;color:#40584D!important;
  line-height:1.2!important;
}
.st-key-top_navigation [role="radiogroup"] label>div:first-child{
  display:none!important;
}

/* Page headers deliberately spacious with no decorative background. */
.job-hero{padding:1.1rem 0 1.15rem;margin-bottom:.7rem;}
.job-hero h1{margin:.18rem 0 .4rem!important;}
.job-section-kicker{
  font-size:.70rem;letter-spacing:.11em;font-weight:760;
  text-transform:uppercase;color:#2D816B;margin-bottom:8px;
}
.job-subline{font-size:.94rem;color:var(--muted);line-height:1.5;}

/* Forms and panels: white background, clear outlines, generous gutters. */
[data-testid="stForm"]{
  background:var(--paper)!important;
  border:1px solid var(--border)!important;border-radius:16px!important;
  padding:1.55rem 1.75rem!important;
  box-shadow:0 3px 13px rgba(27,63,41,.025);
}
[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--paper)!important;border-radius:16px!important;
  border-color:var(--border)!important;
  box-shadow:0 2px 10px rgba(20,59,36,.035);
}
[data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
  background:transparent!important;
  padding:1.5rem 1.65rem!important;
  border-radius:16px!important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p{
  margin-top:.2rem;margin-bottom:.45rem;
}
[data-testid="stMetric"]{
  background:var(--paper)!important;border:1px solid var(--border)!important;
  border-radius:15px!important;padding:1.5rem 1.65rem!important;
  min-height:125px;box-shadow:0 2px 10px rgba(27,63,41,.025);
}
[data-testid="stMetricLabel"] p{
  color:var(--muted)!important;font-size:.83rem!important;
  letter-spacing:.015em;
}
[data-testid="stMetricValue"]{
  color:var(--ink)!important;font-size:1.95rem!important;font-weight:750!important;
}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea{
  border-color:#C9D7D0!important;border-radius:10px!important;
  background:var(--paper)!important;color:var(--ink)!important;
  min-height:45px;
}
[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div{
  border-color:#C9D7D0!important;border-radius:10px!important;
  background:var(--paper)!important;color:var(--ink)!important;
}
.stButton button,[data-testid="stDownloadButton"] button,
[data-testid="stLinkButton"] a{
  min-height:44px!important;border-radius:10px!important;
  padding:10px 18px!important;font-weight:680!important;
  background:var(--paper);color:var(--forest);
  border-color:#BFD7CB;
}
.stButton button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{
  background:var(--forest)!important;border-color:var(--forest)!important;
  color:#FFFFFF!important;
}
.stButton button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
  background:#0D5843!important;border-color:#0D5843!important;
}
[data-testid="stDownloadButton"] button{
  background:#E9F5ED!important;color:#0C5A41!important;
  border:1px solid #B7D6C2!important;
}
[data-testid="stDownloadButton"] button:hover{
  background:#D7EDE0!important;border-color:#81B99E!important;
}
[data-testid="stExpander"]{
  background:var(--paper)!important;border:1px solid var(--border)!important;
  border-radius:12px!important;
}
[data-testid="stExpander"] summary{
  padding:11px 16px!important;min-height:46px;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"]{
  padding:12px 19px 19px!important;
}
[data-testid="stTabs"] button{font-weight:630;}
[data-testid="stDataFrame"]{
  border:1px solid var(--border)!important;border-radius:12px!important;
}
/* Real job cards: comfortable text spacing and readable evidence. */
.job-card-top{margin:0 0 14px;}
.job-role{font-size:1.16rem;font-weight:750;line-height:1.42;color:var(--ink);}
.job-meta{font-size:.90rem;line-height:1.55;color:var(--muted);margin-top:7px;}
.job-tags{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px;}
.job-pill{
  display:inline-flex;align-items:center;line-height:1.35;
  font-size:.76rem;font-weight:600;letter-spacing:.002em;
  color:#476057;background:#F1F5F2;
  padding:6px 11px;border:1px solid #DDE7E0;border-radius:30px;
}
.job-pill.mint{background:#E7F4EB;color:#17664D;border-color:#C5E4D0;}
.job-pill.warn{background:#FFF3DF;color:#81560D;border-color:#F1D9A5;}
.job-pill.blue{background:#EBF2FA;color:#325F85;border-color:#CDDEED;}
.job-score{
  font-size:2.0rem;font-weight:770;color:#156B51;
  letter-spacing:-.05em;line-height:1.24;margin-top:12px;
}
.job-score-denom{font-size:.84rem;color:var(--muted);font-weight:540;}
.job-small{color:var(--muted);font-size:.76rem;
  letter-spacing:.06em;text-transform:uppercase;font-weight:620;}
.job-hint{font-size:.82rem;color:var(--muted);}

/* Equal space at small widths; navigation wraps naturally. */
@media(max-width:900px){
 [data-testid="block-container"]{padding:1rem 1.15rem 3.5rem!important;}
 [data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
   padding:1.12rem 1.1rem!important;}
 [data-testid="stForm"]{padding:1.15rem 1.1rem!important;}
 [data-testid="stMetric"]{padding:1.12rem!important;}
 .job-topbar{flex-wrap:wrap;}
 .st-key-top_navigation [role="radiogroup"]{gap:4px!important;padding:6px!important;}
 .st-key-top_navigation [role="radiogroup"] label{padding:9px 11px!important;}
 h1{font-size:1.7rem!important;}
}

/* October 16 modular pass: squared sections, clearer gutters, and strong
   contrast on every dark-green control. Last declarations intentionally win
   over the earlier soft-card rules above. */
:root {
  --page:#F3F5F6;--paper:#FFFFFF;--quiet:#F7F9F8;
  --ink:#20312B;--muted:#617269;--forest:#14634A;
  --border:#D9E1DE;--hover:#EDF4F0;
}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],
[data-testid="stMain"],[data-testid="stMainBlockContainer"],
[data-testid="stHeader"] {
  background-color:var(--page)!important;
}
[data-testid="block-container"]{
  max-width:1460px!important;
  padding:2.1rem 3.1rem 5rem!important;
}
/* Remove the continuous rounded navigation capsule: six distinct tabs
   on a simple rule, each with its own large touch target. */
.job-topbar{
  padding:.1rem 0 1.2rem!important;
  margin-bottom:1.25rem!important;border-bottom:1px solid var(--border);
}
.job-mark{border-radius:2px!important;}
.st-key-top_navigation [role="radiogroup"]{
  background:transparent!important;
  box-shadow:none!important;border:0!important;
  border-bottom:1px solid #CAD8D2!important;
  border-radius:0!important;
  padding:0 0 8px!important;
  gap:10px!important;
}
.st-key-top_navigation [role="radiogroup"] label{
  border-radius:3px!important;
  border:1px solid #D8E2DC!important;
  background:#FFFFFF!important;
  padding:12px 19px!important;
  min-height:47px!important;
  margin:0!important;
}
.st-key-top_navigation [role="radiogroup"] label:hover{
  background:#EDF5F0!important;border-color:#9AB9AA!important;
}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked){
  background:var(--forest)!important;
  border-color:var(--forest)!important;
  box-shadow:none!important;
}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) p,
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) span,
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) *{
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
.st-key-top_navigation [role="radiogroup"] label:not(:has(input:checked)) p{
  color:#244A3B!important;
}
.job-hero{padding:1.1rem 0 1.55rem!important;margin-bottom:.8rem!important;}
.job-hero h1{line-height:1.25!important;}
/* All real modules use the same tidy rectangular geometry instead of bubbles. */
[data-testid="stMetric"],
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"],
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stAlert"]{
  border-radius:4px!important;
  box-shadow:none!important;
}
[data-testid="stMetric"]{
  padding:1.75rem 1.85rem!important;
  min-height:138px;
  border-left:4px solid #94B6A6!important;
}
[data-testid="stForm"]{
  padding:2rem 2.15rem!important;
  border-top:3px solid #9ABCAA!important;
}
[data-testid="stVerticalBlockBorderWrapper"]{
  background:#FFFFFF!important;
  border:1px solid #D5DFDA!important;
  border-left:4px solid #9BBCAA!important;
  margin-bottom:13px!important;
}
[data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
  padding:1.95rem 2.1rem!important;
  background:#FFFFFF!important;
}
/* Spacing inside bordered cards, not only around them. */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"]{
  row-gap:1rem!important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p{
  margin:.3rem 0 .7rem!important;
  line-height:1.65!important;
}
[data-testid="stExpander"] summary{
  padding:14px 18px!important;min-height:48px;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"]{
  padding:1.1rem 1.6rem 1.5rem!important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"]>div>div,
[data-testid="stMultiSelect"]>div>div{
  border-radius:3px!important;
}
.stButton button,[data-testid="stDownloadButton"] button,
[data-testid="stLinkButton"] a,
[data-testid="stFormSubmitButton"] button{
  border-radius:3px!important;min-height:47px!important;
  padding:11px 19px!important;
}
/* The old global p color could override white labels on filled controls.
   Bind the descendants' colors, not just the button element. */
.stButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button{
  background:var(--forest)!important;
  border-color:var(--forest)!important;
  color:#FFFFFF!important;
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
  background:#0D4D39!important;border-color:#0D4D39!important;
}
.stButton button[kind="primary"]:hover *,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover *,
[data-testid="stDownloadButton"] button:hover *{
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
[data-testid="stDownloadButton"] button:focus-visible,
.stButton button[kind="primary"]:focus-visible{
  outline:3px solid #A5D9C0!important;outline-offset:3px;
}
/* Tags resemble small rectangular metadata chips, never floating pills. */
.job-pill,.job-pill.mint,.job-pill.warn,.job-pill.blue{
  border-radius:2px!important;padding:6px 10px!important;
  font-size:.76rem!important;line-height:1.35!important;
}
.job-pill.mint{
  background:var(--forest)!important;border-color:var(--forest)!important;
  color:#FFFFFF!important;
}
.job-card-top{margin:0 0 1rem!important;}
.job-role{font-size:1.18rem;line-height:1.47!important;}
.job-meta{line-height:1.65!important;margin-top:9px!important;}
.job-tags{gap:8px!important;margin-top:16px!important;}
.job-score{margin-top:15px!important;}
/* Distinct section heading sits outside cards; minimal rule underneath. */
.job-module-heading{
  margin:2.15rem 0 1.1rem;
  padding:0 0 .78rem;border-bottom:1px solid #CEDAD3;
  font-size:1.12rem;font-weight:760;letter-spacing:-.018em;
  color:var(--ink);
}
.job-module-caption{
  color:var(--muted);font-size:.9rem;line-height:1.55;
  margin:-.5rem 0 1.3rem;
}
@media(max-width:900px){
 [data-testid="block-container"]{padding:1.1rem 1.1rem 4rem!important;}
 [data-testid="stMetric"]{padding:1.35rem 1.4rem!important;}
 [data-testid="stForm"]{padding:1.45rem 1.35rem!important;}
 [data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
   padding:1.45rem 1.35rem!important;
 }
 .st-key-top_navigation [role="radiogroup"]{gap:6px!important;}
 .st-key-top_navigation [role="radiogroup"] label{
   padding:11px 13px!important;min-height:43px!important;
 }
}


/* No colored module outlines. Panels are separated by whitespace and an
   understated neutral shadow, never green sidebars or green top borders. */
[data-testid="stMetric"],
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"],
[data-testid="stDataFrame"]{
  border:0!important;
  border-left:0!important;
  border-right:0!important;
  border-top:0!important;
  border-bottom:0!important;
  box-shadow:0 3px 16px rgba(31,47,43,.07)!important;
  background:#FFFFFF!important;
}
[data-testid="stVerticalBlockBorderWrapper"]>div[data-testid="stVerticalBlock"]{
  border:0!important;
  background:#FFFFFF!important;
}
[data-testid="stMetric"]{padding:1.8rem 1.95rem!important;}
[data-testid="stForm"]{padding:2rem 2.2rem!important;}
[data-testid="stVerticalBlockBorderWrapper"]{
  margin-bottom:18px!important;
}
.job-topbar,.job-module-heading,
.st-key-top_navigation [role="radiogroup"]{
  border-bottom:0!important;
}
.job-module-heading{
  padding-bottom:.5rem!important;
  margin-top:2.4rem!important;
}
.st-key-top_navigation [role="radiogroup"] label{
  border:0!important;
}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked),
.st-key-top_navigation [role="radiogroup"] label:hover{
  border:0!important;
}
.job-pill.mint{
  border:0!important;
  color:#FFFFFF!important;
}
.stButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button,
.stButton button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
[data-testid="stDownloadButton"] button:hover{
  border:0!important;
  color:#FFFFFF!important;
}
@media(max-width:900px){
  [data-testid="stMetric"]{padding:1.3rem 1.4rem!important;}
  [data-testid="stForm"]{padding:1.5rem 1.4rem!important;}
}

</style>
"""


def _safe(value):
    return escape(str(value if value is not None else ""),quote=True)


def brand(version=""):
    return ('<div class="job-topbar"><div class="job-brand">'
            '<span class="job-mark" aria-hidden="true"></span>'
            '<span class="job-brand-title">AI Job Finder</span></div>'
            + ('<span class="job-version">Version '+_safe(version)+'</span>'
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
