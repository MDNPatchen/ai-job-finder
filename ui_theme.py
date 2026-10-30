"""Dark presentation layer for AI Job Finder.

Layout follows the MDN billing app (sidebar navigation with a wordmark,
condensed uppercase labels, Inter body text, bordered cards with an accent
stripe on metrics) on a charcoal-grey palette with a steel-blue accent.

All dynamic strings are HTML-escaped before insertion into a Streamlit
markdown block. Change colors in PALETTE and in .streamlit/config.toml.
"""
from html import escape

PALETTE={
    "background":"#303338",   # page: off-grey charcoal, not black
    "sidebar":"#2A2D31",
    "panel":"#3A3E44",        # cards, forms, metrics
    "raised":"#454A51",       # inputs, secondary buttons
    "border":"#565C64",
    "text":"#F3F4F6",
    "muted":"#C3C8CF",
    "accent":"#3563C9",       # buttons (white text 5.6:1)
    "accent_bright":"#9DBDFF",  # accent text on grey (5.7:1 on cards)
    "accent_tint":"#3A4A6B",  # active navigation row, highlight pills
}

WORDMARK_FONT="'Outfit', 'Segoe UI', system-ui, sans-serif"
TITLE_FONT="'Outfit', 'Segoe UI', system-ui, sans-serif"
HEADING_FONT="'Barlow Condensed', 'Arial Narrow', sans-serif"
BODY_FONT="'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"

_CSS=r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Outfit:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');
:root{--page:__background__;--side:__sidebar__;--paper:__panel__;--raised:__raised__;--line:__border__;
 --ink:__text__;--muted:__muted__;--accent:__accent__;--accent-text:__accent_bright__;--tint:__accent_tint__;
 --head:__HEAD__;--title:__TITLE__;--body:__BODY__;--mark:__MARK__;}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--page)!important;color:var(--ink)!important;}
[data-testid="stHeader"]{background:transparent!important;}
[data-testid="stDecoration"],[data-testid="stSidebarNav"]{display:none!important;}
.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp textarea,.stApp button{font-family:var(--body);}

/* ---- Page shell: structural wrappers are never styled as cards ---- */
[data-testid="stMainBlockContainer"],.block-container{
 box-sizing:border-box!important;width:100%!important;max-width:1280px!important;
 margin-inline:auto!important;padding:56px 48px 64px!important;
}
.st-key-dashboard_content{padding:0!important;background:transparent!important;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:var(--head)!important;color:var(--ink)!important;font-weight:700!important;letter-spacing:.01em;line-height:1.15!important;}
.stApp h1{font-family:var(--title)!important;font-size:2.3rem!important;letter-spacing:-.01em;}
.stApp h2{font-size:1.6rem!important;}.stApp h3{font-size:1.35rem!important;}
p,li,[data-testid="stMarkdownContainer"]{color:var(--ink);line-height:1.55;}
[data-testid="stCaptionContainer"] p,[data-testid="stWidgetLabel"] p{color:var(--muted)!important;font-size:.85rem!important;}
hr{border-color:var(--line)!important;}

/* ---- Sidebar: wordmark and navigation, as in the billing app ---- */
section[data-testid="stSidebar"]{background:var(--side)!important;border-right:1px solid var(--line);}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{background:var(--side)!important;}
.job-topbar{padding:4px 0 0;}
.job-brand{display:flex;flex-direction:column;}
.job-brand-title{font-family:var(--mark);font-weight:800;font-size:1.9rem;line-height:1.05;color:var(--accent-text);letter-spacing:-.02em;}
.job-brand-sub{font-family:var(--head);font-weight:600;font-size:.85rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-top:6px;}
.job-version{display:block;font-size:.75rem;color:var(--muted);margin:4px 0 20px;}
.st-key-top_navigation [data-testid="stWidgetLabel"]{display:none!important;}
.st-key-top_navigation [role="radiogroup"]{display:flex!important;flex-direction:column!important;gap:2px!important;}
.st-key-top_navigation [role="radiogroup"] label{box-sizing:border-box;margin:0!important;padding:10px 12px!important;min-height:44px;width:100%;
 border-left:3px solid transparent;border-radius:6px;background:transparent;cursor:pointer;align-items:center;}
.st-key-top_navigation [role="radiogroup"] label>div:first-child{display:none!important;}
.st-key-top_navigation [role="radiogroup"] label p{color:var(--ink)!important;font-size:.95rem;font-weight:600;}
.st-key-top_navigation [role="radiogroup"] label:hover{background:var(--tint);}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked){background:var(--tint);border-left-color:var(--accent-text);}
.st-key-top_navigation [role="radiogroup"] label:has(input:checked) p{color:var(--accent-text)!important;}

/* ---- Page headings ---- */
.job-hero{margin:0 0 22px;}.job-hero h1{margin:0 0 6px!important;padding:0!important;}
.job-subline{color:var(--muted);font-size:.95rem;line-height:1.55;max-width:70ch;}
.job-module-heading{margin:28px 0 12px;font-family:var(--head);font-size:1.05rem;font-weight:700;
 letter-spacing:.1em;text-transform:uppercase;color:var(--muted);}
.job-module-caption{color:var(--muted);font-size:.85rem;margin-bottom:16px;}

/* ---- Cards: explicit modules only, never root wrappers ---- */
[data-testid="stForm"],[data-testid="stMetric"],[data-testid="stExpander"],[class*="st-key-job_card_"]{
 background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:10px!important;box-shadow:none;
}
[data-testid="stForm"]{padding:24px!important;}
[class*="st-key-job_card_"]{padding:22px 24px!important;}
[data-testid="stMetric"]{border-left:5px solid var(--accent)!important;padding:16px 20px!important;min-height:108px;}
[data-testid="stMetricLabel"] p{font-family:var(--head)!important;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)!important;font-size:.85rem!important;}
[data-testid="stMetricValue"]{font-family:var(--head)!important;color:var(--accent-text)!important;font-size:2.6rem!important;font-weight:700;line-height:1.15;}
[data-testid="stExpander"] summary{padding:12px 16px!important;min-height:44px;}
[data-testid="stExpanderDetails"]{padding:16px 20px!important;}
[data-testid="stAlert"]{box-sizing:border-box;max-width:100%;border-radius:8px;}
[data-testid="stAlert"] p{font-size:.93rem;line-height:1.5;}

/* ---- Inputs and buttons ---- */
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div,[data-testid="stDateInput"] input{background:var(--raised)!important;color:var(--ink)!important;border-radius:6px!important;min-height:44px;font-size:.93rem!important;}
input::placeholder,textarea::placeholder{color:var(--muted)!important;opacity:1;}
.stButton button,[data-testid="stDownloadButton"] button,[data-testid="stLinkButton"] a,[data-testid="stFormSubmitButton"] button{min-height:44px;border-radius:6px!important;padding:10px 16px!important;background:var(--raised);color:var(--ink);border:1px solid var(--line);font-weight:600;}
.stButton button:hover,[data-testid="stLinkButton"] a:hover{border-color:var(--accent-text);color:var(--accent-text);}
button[kind="primary"],[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button{background:var(--accent)!important;border-color:var(--accent)!important;color:white!important;}
button[kind="primary"] *,[data-testid="stDownloadButton"] button *,[data-testid="stFormSubmitButton"] button *{color:white!important;}
button:focus-visible,input:focus-visible,textarea:focus-visible,.st-key-top_navigation label:has(input:focus-visible){outline:2px solid var(--accent-text)!important;outline-offset:3px;}

/* ---- Job listings ---- */
.job-card-top{min-width:0;}
.job-role{font-family:var(--title);font-size:1.3rem;font-weight:700;line-height:1.25;letter-spacing:-.005em;overflow-wrap:anywhere;}
.job-meta{font-size:.9rem;color:var(--muted);margin-top:6px;}
.job-tags{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0;}
.job-pill{display:inline-flex;align-items:center;font-size:.75rem;font-weight:600;padding:4px 11px;border-radius:999px;background:var(--raised);color:var(--ink);border:1px solid var(--line);}
.job-pill.mint{background:var(--tint);color:#CFE0FF;border-color:#4C5F86;}
.job-pill.warn{background:#4E4330;color:#F6D7A1;border-color:#6A5A3E;}
.job-pill.blue{background:#4A4366;color:#E0D7FF;border-color:#605883;}
.job-small{font-family:var(--head);font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600;}
.job-score{font-family:var(--head);font-size:2.4rem;font-weight:700;color:var(--accent-text);line-height:1.1;}
.job-score-denom{font-size:.9rem;color:var(--muted);}
.job-hint{font-size:.85rem;color:var(--muted);}

@media(max-width:900px){
 [data-testid="stMainBlockContainer"],.block-container{padding:56px 28px 48px!important;}
 .stApp h1{font-size:2.1rem!important;}
}
@media(max-width:520px){
 [data-testid="stMainBlockContainer"],.block-container{padding:56px 20px 40px!important;}
 .stApp h1{font-size:1.8rem!important;}
 [data-testid="stForm"],[class*="st-key-job_card_"]{padding:16px!important;}
 [data-testid="stMetric"]{padding:14px 16px!important;}
 [data-testid="stMetricValue"]{font-size:2.1rem!important;}
}
</style>
"""

APP_CSS=_CSS.replace('__HEAD__',HEADING_FONT).replace('__BODY__',BODY_FONT).replace('__MARK__',WORDMARK_FONT).replace('__TITLE__',TITLE_FONT)
for _name,_value in PALETTE.items():
    APP_CSS=APP_CSS.replace('__'+_name+'__',_value)


def _safe(value):
    return escape(str(value if value is not None else ""),quote=True)


def brand(version=""):
    """Sidebar wordmark, laid out like the billing app's MDN block."""
    return ('<div class="job-topbar"><div class="job-brand">'
            '<span class="job-brand-title">AI Job Finder</span>'
            '<span class="job-brand-sub">Career Search</span></div>'
            + ('<span class="job-version">Version '+_safe(version)+'</span>'
               if version else '') + '</div>')


def hero(title,subtitle=""):
    # Page title and caption, as in the billing app's page_title().
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
