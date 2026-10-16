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
:root{--page:#27342F;--paper:#34443D;--raised:#3C4E45;--ink:#F1F6F2;--muted:#BBCDC2;--forest:#257B5B;--divider:#50655A;}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stHeader"]{background:var(--page)!important;color:var(--ink)!important;}
[data-testid="stDecoration"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],[data-testid="collapsedControl"]{display:none!important;}
/* One page shell. Structural wrappers are deliberately not styled as cards. */
[data-testid="stMainBlockContainer"],.block-container{
 box-sizing:border-box!important;width:100%!important;max-width:1280px!important;
 margin-inline:auto!important;padding:88px 48px 64px!important;
}
.st-key-dashboard_content{padding:0!important;background:transparent!important;}
h1,h2,h3,h4{color:var(--ink)!important;letter-spacing:-.025em;line-height:1.25!important;}
h1{font-size:2rem!important;font-weight:700!important;}
h2{font-size:1.35rem!important;}h3{font-size:1.12rem!important;}
p,li,[data-testid="stMarkdownContainer"]{color:var(--ink);line-height:1.55;}
[data-testid="stCaptionContainer"] p,[data-testid="stWidgetLabel"] p{color:var(--muted)!important;font-size:.85rem!important;}
.job-topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:0 0 20px;border-bottom:1px solid var(--divider);}
.job-brand{display:flex;align-items:center;gap:12px;}
.job-brand-title{font-size:1.2rem;font-weight:750;color:var(--ink);letter-spacing:-.02em;}
.job-mark{width:28px;height:28px;background:var(--forest);border-radius:7px;display:inline-block;position:relative;flex:none;}
.job-mark:after{content:"";position:absolute;left:10px;top:6px;width:7px;height:13px;border-left:2px solid white;border-bottom:2px solid white;transform:rotate(-40deg);}
.job-version{color:var(--muted);font-size:.8rem;white-space:nowrap;}
.st-key-top_navigation [data-testid="stWidgetLabel"]{display:none!important;}
.st-key-top_navigation [role="radiogroup"]{display:flex!important;flex-wrap:wrap!important;gap:6px!important;padding:8px 0!important;}
.st-key-top_navigation [role="radiogroup"] label{margin:0!important;padding:12px 16px!important;min-height:44px;border-radius:7px;background:transparent;cursor:pointer;}
.st-key-top_navigation [role="radiogroup"] label>div:first-child{display:none!important;}
.st-key-top_navigation [role="radiogroup"] label p{color:var(--muted)!important;font-size:.88rem;font-weight:600;}
.st-key-top_navigation [role="radiogroup"] label:hover{background:var(--paper);}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked){background:var(--forest);}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) p{color:white!important;}
.job-hero{margin:22px 0 24px;}.job-hero h1{margin:0 0 8px!important;}
.job-subline{color:var(--muted);font-size:.95rem;line-height:1.55;max-width:70ch;}
.job-module-heading{margin:28px 0 12px;font-size:1.15rem;font-weight:700;}
.job-module-caption{color:var(--muted);font-size:.85rem;margin-bottom:16px;}
/* Compact independent modules: explicit cards only, never root wrappers. */
[data-testid="stForm"],[data-testid="stMetric"],[data-testid="stExpander"],[class*="st-key-job_card_"]{
 background:var(--paper)!important;border:1px solid rgba(187,205,194,.15)!important;border-radius:10px!important;box-shadow:0 4px 16px rgba(12,22,18,.10);
}
[data-testid="stForm"]{padding:24px!important;}
[class*="st-key-job_card_"]{padding:24px!important;}
[data-testid="stMetric"]{padding:22px 24px!important;min-height:116px;}
[data-testid="stMetricLabel"] p{color:var(--muted)!important;font-size:.85rem!important;}
[data-testid="stMetricValue"]{color:var(--ink)!important;font-size:2rem!important;font-weight:700;}
[data-testid="stExpander"] summary{padding:12px 16px!important;min-height:44px;}
[data-testid="stExpanderDetails"]{padding:16px 20px!important;}
[data-testid="stAlert"]{box-sizing:border-box;max-width:100%;border-radius:8px;}
[data-testid="stAlert"] p{font-size:.93rem;line-height:1.5;}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div,[data-testid="stDateInput"] input{background:var(--raised)!important;color:var(--ink)!important;border-radius:6px!important;min-height:44px;font-size:.93rem!important;}
input::placeholder,textarea::placeholder{color:var(--muted)!important;opacity:1;}
.stButton button,[data-testid="stDownloadButton"] button,[data-testid="stLinkButton"] a,[data-testid="stFormSubmitButton"] button{min-height:44px;border-radius:6px!important;padding:10px 16px!important;background:var(--raised);color:var(--ink);font-weight:600;}
button[kind="primary"],[data-testid="stDownloadButton"] button{background:var(--forest)!important;color:white!important;}
button[kind="primary"] *,[data-testid="stDownloadButton"] button *{color:white!important;}
button:focus-visible,input:focus-visible,textarea:focus-visible,.st-key-top_navigation label:has(input:focus-visible){outline:2px solid #8DD4B2!important;outline-offset:3px;}
.job-role{font-size:1.2rem;font-weight:700;line-height:1.4;overflow-wrap:anywhere;}
.job-meta{font-size:.9rem;color:var(--muted);margin-top:7px;}
.job-tags{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0;}
.job-pill{display:inline-flex;font-size:.75rem;font-weight:600;padding:5px 9px;border-radius:5px;background:var(--raised);color:var(--ink);}
.job-pill.mint{background:var(--forest);color:white;}.job-pill.warn{background:#63533B;color:#F6DEAD;}.job-pill.blue{background:#3C5660;color:#D7EFF5;}
.job-score{font-size:2rem;font-weight:700;color:#9FE3BC;line-height:1.2;}.job-score-denom{font-size:.85rem;color:var(--muted);}
.job-small{font-size:.72rem;letter-spacing:.06em;color:var(--muted);font-weight:600;}.job-hint{font-size:.85rem;color:var(--muted);}
hr{border-color:var(--divider)!important;}
@media(max-width:900px){
 [data-testid="stMainBlockContainer"],.block-container{padding:80px 28px 48px!important;}
 .st-key-top_navigation [role="radiogroup"] label{padding:10px 12px!important;}
}
@media(max-width:520px){
 [data-testid="stMainBlockContainer"],.block-container{padding:76px 20px 40px!important;}
 .job-brand-title{font-size:1rem;}.job-version{font-size:.72rem;}.job-topbar{gap:8px;}
 .job-hero{margin:16px 0 20px;}h1{font-size:1.65rem!important;}
 [data-testid="stForm"],[class*="st-key-job_card_"]{padding:16px!important;}
 [data-testid="stMetric"]{padding:18px!important;}
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
    return ('<div class="job-hero">'
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
