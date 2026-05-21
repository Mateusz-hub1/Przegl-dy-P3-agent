import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import io
import re
import gspread
from google.oauth2.service_account import Credentials
import time
import base64
from pathlib import Path

# ---------------------------------------------------------------------------
# KONFIGURACJA STRONY
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="KORCZ — Skaner DDU / P3",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🚂",
)

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
if "wyniki"        not in st.session_state: st.session_state.wyniki = []
if "edytowany_idx" not in st.session_state: st.session_state.edytowany_idx = None
if "tryb"          not in st.session_state: st.session_state.tryb = "AUTO"
if "theme"         not in st.session_state: st.session_state.theme = "dark"

# ---------------------------------------------------------------------------
# CSS — DARK / LIGHT z przełącznikiem
# ---------------------------------------------------------------------------
IS_DARK = st.session_state.theme == "dark"

DARK_CSS = """
  :root {
    --bg:           #04040a;
    --bg2:          rgba(255,255,255,.03);
    --bg3:          rgba(255,255,255,.06);
    --border:       rgba(255,255,255,.07);
    --border-hover: rgba(255,255,255,.14);
    --text-primary: rgba(255,255,255,.92);
    --text-sec:     rgba(255,255,255,.45);
    --text-muted:   rgba(255,255,255,.22);
    --card-top:     linear-gradient(90deg, transparent, rgba(229,0,26,.35), rgba(120,60,255,.25), transparent);
    --input-bg:     rgba(255,255,255,.04);
    --input-focus:  rgba(229,0,26,.06);
    --metric-hover: rgba(229,0,26,.07);
    --progress-bg:  rgba(255,255,255,.07);
    --expand-bg:    rgba(255,255,255,.03);
    --aurora1: rgba(99,51,255,.17);
    --aurora2: rgba(0,200,255,.11);
    --aurora3: rgba(229,0,26,.09);
    --aurora4: rgba(120,40,200,.08);
  }
"""

LIGHT_CSS = """
  :root {
    --bg:           #f3f2ee;
    --bg2:          #ffffff;
    --bg3:          #f7f6f2;
    --border:       rgba(0,0,0,.08);
    --border-hover: rgba(0,0,0,.16);
    --text-primary: #111111;
    --text-sec:     #555555;
    --text-muted:   #999999;
    --card-top:     linear-gradient(90deg, transparent, rgba(229,0,26,.3), rgba(120,60,255,.15), transparent);
    --input-bg:     #fafaf8;
    --input-focus:  rgba(229,0,26,.04);
    --metric-hover: rgba(229,0,26,.04);
    --progress-bg:  rgba(0,0,0,.07);
    --expand-bg:    #fafaf8;
    --aurora1: rgba(99,51,255,.06);
    --aurora2: rgba(0,180,230,.05);
    --aurora3: rgba(229,0,26,.04);
    --aurora4: rgba(120,40,200,.04);
  }
"""

THEME_CSS = DARK_CSS if IS_DARK else LIGHT_CSS

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap');

  {THEME_CSS}

  /* ─── RESET & TŁO ─── */
  *, *::before, *::after {{ box-sizing: border-box; }}

  .stApp {{
    background: var(--bg) !important;
    font-family: 'Plus Jakarta Sans', sans-serif;
    min-height: 100vh;
  }}

  /* Aurora — tylko translateY, bez scale (fix rozciągania) */
  .stApp::before {{
    content: '';
    position: fixed;
    inset: -10%;
    width: 120%;
    height: 120%;
    z-index: 0;
    pointer-events: none;
    background:
      radial-gradient(ellipse 900px 700px at 15% 15%,  var(--aurora1) 0%, transparent 55%),
      radial-gradient(ellipse 800px 600px at 88% 20%,  var(--aurora2) 0%, transparent 55%),
      radial-gradient(ellipse 700px 800px at 50% 85%,  var(--aurora3) 0%, transparent 55%),
      radial-gradient(ellipse 1000px 500px at 72% 55%, var(--aurora4) 0%, transparent 50%);
    animation: aurora-drift 20s ease-in-out infinite alternate;
  }}

  @keyframes aurora-drift {{
    0%   {{ transform: translateY(0px)   translateX(0px);   }}
    25%  {{ transform: translateY(-18px) translateX(8px);   }}
    50%  {{ transform: translateY(-8px)  translateX(-12px); }}
    75%  {{ transform: translateY(-22px) translateX(5px);   }}
    100% {{ transform: translateY(-10px) translateX(-6px);  }}
  }}

  section[data-testid="stMain"],
  section[data-testid="stMain"] > div {{ position: relative; z-index: 1; }}

  header[data-testid="stHeader"]  {{ background: transparent !important; }}
  #MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; }}
  section[data-testid="stSidebar"] {{ display: none; }}

  .block-container {{
    padding: 2rem 3rem 4rem !important;
    max-width: 1440px !important;
  }}

  /* ─── HEADER ─── */
  .korcz-header {{
    display: flex; align-items: center; gap: 24px;
    padding: 26px 0 22px;
    margin-bottom: 36px;
    border-bottom: 1px solid var(--border);
    position: relative;
  }}
  .korcz-header::after {{
    content: '';
    position: absolute; bottom: -1px; left: 0;
    width: 260px; height: 1px;
    background: linear-gradient(90deg, #e5001a, #ff6b35, transparent);
  }}
  .korcz-brand {{ font-family: 'Syne', sans-serif; line-height: 1; }}
  .korcz-brand .name {{
    font-size: 2.5rem; font-weight: 800; letter-spacing: 4px;
    background: linear-gradient(135deg, #ff3a50 0%, #ff7255 55%, #ffaa44 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }}
  .korcz-brand .tagline {{
    font-size: .7rem; color: var(--text-muted);
    letter-spacing: 4px; text-transform: uppercase; margin-top: 4px;
  }}
  .korcz-header-meta {{
    margin-left: auto; text-align: right;
    display: flex; flex-direction: column; gap: 6px; align-items: flex-end;
  }}
  .version-tag {{
    font-family: 'Syne', sans-serif; font-size: .6rem;
    letter-spacing: 3px; color: var(--text-muted); text-transform: uppercase;
  }}
  .status-badge {{
    display: flex; align-items: center; gap: 6px;
    background: rgba(0,200,100,.07);
    border: 1px solid rgba(0,200,100,.2);
    border-radius: 20px; padding: 4px 12px;
  }}
  .status-dot {{
    width: 6px; height: 6px; border-radius: 50%; background: #00d455;
    box-shadow: 0 0 8px #00d455;
    animation: pulse-green 2.5s ease-in-out infinite;
  }}
  @keyframes pulse-green {{
    0%,100% {{ box-shadow: 0 0 5px #00d455; }}
    50%      {{ box-shadow: 0 0 14px #00d455, 0 0 28px rgba(0,212,85,.5); }}
  }}
  .status-text {{
    font-size: .68rem; color: #00d455;
    letter-spacing: 2px; text-transform: uppercase;
    font-family: 'Syne', sans-serif; font-weight: 600;
  }}

  /* ─── GLASS KARTY ─── */
  .card {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    position: relative; overflow: hidden;
    transition: border-color .3s;
  }}
  .card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: var(--card-top);
  }}
  .card:hover {{ border-color: var(--border-hover); }}
  .card-header {{
    font-family: 'Syne', sans-serif; font-size: .75rem; font-weight: 700;
    color: var(--text-muted); letter-spacing: 4px; text-transform: uppercase;
    margin-bottom: 20px; padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 10px;
  }}
  .ch-accent {{ color: #e5001a; }}

  /* ─── BUTTONS ─── */
  .stButton > button {{
    background: var(--bg3) !important;
    color: var(--text-sec) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: .78rem !important; font-weight: 700 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    padding: 10px 18px !important;
    transition: all .2s ease !important;
  }}
  .stButton > button:hover {{
    background: rgba(229,0,26,.1) !important;
    border-color: rgba(229,0,26,.4) !important;
    color: var(--text-primary) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(229,0,26,.15) !important;
  }}
  .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, rgba(229,0,26,.75), rgba(170,0,70,.65)) !important;
    border-color: rgba(229,0,26,.5) !important;
    color: #fff !important;
    box-shadow: 0 0 18px rgba(229,0,26,.2) !important;
  }}
  .stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, #e5001a, #b8003a) !important;
    box-shadow: 0 0 28px rgba(229,0,26,.4), 0 4px 16px rgba(229,0,26,.25) !important;
    transform: translateY(-2px) !important;
  }}
  .btn-send > button {{
    background: linear-gradient(135deg, #e5001a 0%, #aa0030 45%, #6b20d0 100%) !important;
    color: #fff !important; border: none !important;
    border-radius: 12px !important; font-size: .95rem !important;
    letter-spacing: 3px !important; padding: 14px 24px !important;
    box-shadow: 0 0 36px rgba(229,0,26,.28), 0 4px 24px rgba(107,32,208,.2) !important;
  }}
  .btn-send > button:hover {{
    box-shadow: 0 0 52px rgba(229,0,26,.45), 0 8px 36px rgba(107,32,208,.35) !important;
    transform: translateY(-2px) scale(1.01) !important;
  }}
  .btn-ghost > button {{
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--text-muted) !important;
  }}
  .btn-ghost > button:hover {{
    border-color: rgba(255,60,60,.4) !important;
    color: #ff5555 !important;
    background: rgba(255,0,0,.04) !important;
    box-shadow: none !important;
  }}

  /* Theme toggle button */
  .btn-theme > button {{
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-sec) !important;
    border-radius: 20px !important;
    font-size: .72rem !important; letter-spacing: 2px !important;
    padding: 6px 16px !important;
  }}
  .btn-theme > button:hover {{
    border-color: rgba(229,0,26,.3) !important;
    color: var(--text-primary) !important;
    background: var(--bg3) !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* ─── FILE UPLOADER ─── */
  [data-testid="stFileUploader"] {{
    background: var(--input-bg) !important;
    border: 1px dashed rgba(229,0,26,.25) !important;
    border-radius: 12px !important; padding: 28px !important;
    transition: all .3s ease !important;
  }}
  [data-testid="stFileUploader"]:hover {{
    border-color: rgba(229,0,26,.5) !important;
    background: var(--input-focus) !important;
  }}
  [data-testid="stFileUploaderDropzone"] p  {{ color: var(--text-muted) !important; }}
  [data-testid="stFileUploaderDropzone"] small {{ color: var(--text-muted) !important; }}

  /* ─── METRYKI ─── */
  [data-testid="stMetric"] {{
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important; padding: 20px 22px !important;
    position: relative !important; overflow: hidden !important;
    transition: all .25s ease !important;
  }}
  [data-testid="stMetric"]:hover {{
    background: var(--metric-hover) !important;
    border-color: rgba(229,0,26,.22) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(229,0,26,.08) !important;
  }}
  [data-testid="stMetric"]::after {{
    content: ''; position: absolute; bottom: 0; left: 0; right: 0;
    height: 2px; background: linear-gradient(90deg, #e5001a, transparent); opacity: .5;
  }}
  [data-testid="stMetricLabel"] {{
    color: var(--text-muted) !important; font-size: .62rem !important;
    letter-spacing: 3px !important; text-transform: uppercase !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
  }}
  [data-testid="stMetricValue"] {{
    color: var(--text-primary) !important; font-family: 'Syne', sans-serif !important;
    font-size: 2.3rem !important; font-weight: 800 !important; line-height: 1.1 !important;
  }}

  /* ─── BADGES ─── */
  .badge {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 6px;
    font-size: .62rem; font-weight: 700;
    font-family: 'Syne', sans-serif; letter-spacing: 1.5px; text-transform: uppercase;
  }}
  .badge::before {{ content: ''; width: 5px; height: 5px; border-radius: 50%; display: inline-block; }}
  .badge-ok    {{ background: rgba(0,212,85,.1);  color: #00c44d; border: 1px solid rgba(0,212,85,.25); }}
  .badge-ok::before {{ background: #00d455; box-shadow: 0 0 5px #00d455; }}
  .badge-warn  {{ background: rgba(255,165,0,.1); color: #e09030; border: 1px solid rgba(255,165,0,.25); }}
  .badge-warn::before {{ background: #ffaa33; }}
  .badge-error {{ background: rgba(255,50,80,.1); color: #e03050; border: 1px solid rgba(255,50,80,.25); }}
  .badge-error::before {{ background: #ff4060; }}
  .badge-sent  {{ background: rgba(60,140,255,.1); color: #3a7fd5; border: 1px solid rgba(60,140,255,.25); }}
  .badge-sent::before {{ background: #5599ff; }}
  .badge-p3    {{ background: rgba(80,120,255,.08); color: #4070cc; border: 1px solid rgba(80,120,255,.2); }}
  .badge-p3::before {{ background: #88aaff; }}
  .badge-ddu   {{ background: rgba(229,0,26,.08); color: #c0001a; border: 1px solid rgba(229,0,26,.2); }}
  .badge-ddu::before {{ background: #ff5566; }}

  /* ─── TABELA ─── */
  .tbl-head {{
    color: var(--text-muted) !important; font-size: .58rem !important;
    letter-spacing: 2.5px; text-transform: uppercase;
    font-family: 'Syne', sans-serif; font-weight: 700;
  }}
  .tbl-num  {{ color: var(--text-muted); font-size: .8rem; }}
  .tbl-file {{ color: var(--text-sec); font-size: .74rem; word-break: break-all; line-height: 1.3; }}
  .type-bar-p3  {{ border-left: 2px solid rgba(100,140,255,.5); padding-left: 8px; }}
  .type-bar-ddu {{ border-left: 2px solid rgba(229,0,26,.55); padding-left: 8px; }}
  .wagon-num {{ font-family: 'Syne', sans-serif; font-size: .9rem; color: var(--text-primary); font-weight: 700; letter-spacing: 1px; }}
  .tbl-meta    {{ color: var(--text-sec);  font-size: .76rem; }}
  .tbl-meta-hi {{ color: var(--text-primary); font-size: .76rem; }}

  /* ─── INPUTS ─── */
  .stTextInput > label, .stSelectbox > label {{
    color: var(--text-muted) !important; font-size: .62rem !important;
    letter-spacing: 3px !important; text-transform: uppercase !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
  }}
  .stTextInput > div > div > input {{
    background: var(--input-bg) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: .9rem !important; padding: 10px 14px !important;
  }}
  .stTextInput > div > div > input:focus {{
    border-color: rgba(229,0,26,.55) !important;
    box-shadow: 0 0 0 3px rgba(229,0,26,.08) !important;
    background: var(--input-focus) !important;
  }}
  .stSelectbox > div > div {{
    background: var(--input-bg) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
  }}

  /* ─── PROGRESS ─── */
  .stProgress > div > div > div {{
    background: linear-gradient(90deg, #e5001a, #ff4060) !important;
    border-radius: 3px !important;
    box-shadow: 0 0 10px rgba(229,0,26,.45) !important;
  }}
  .stProgress > div > div {{
    background: var(--progress-bg) !important; border-radius: 3px !important;
  }}

  /* ─── EXPANDER ─── */
  .streamlit-expanderHeader {{
    background: var(--expand-bg) !important; color: var(--text-muted) !important;
    font-size: .74rem !important; border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    font-family: 'Syne', sans-serif !important;
  }}
  .streamlit-expanderContent {{
    background: var(--input-bg) !important;
  }}

  /* ─── ALERTY ─── */
  .stAlert {{ border-radius: 10px !important; }}
  [data-baseweb="notification"] {{
    background: rgba(0,212,85,.06) !important;
    border-left: 3px solid #00d455 !important;
    border-radius: 10px !important;
  }}

  /* ─── INFO BOX ─── */
  .info-box {{
    background: var(--bg3);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 13px 18px; margin: 10px 0;
    display: flex; align-items: center; gap: 12px;
    font-size: .8rem; color: var(--text-sec);
  }}

  /* ─── SEPARATOR ─── */
  hr {{ border: none !important; border-top: 1px solid var(--border) !important; margin: 6px 0 !important; }}

  /* ─── EDIT LABEL ─── */
  .edit-lbl {{
    font-family: 'Syne', sans-serif; font-size: .58rem;
    letter-spacing: 3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px;
  }}

  /* ─── FOOTER ─── */
  .korcz-footer {{
    text-align: center; margin-top: 56px; padding-top: 22px;
    border-top: 1px solid var(--border);
    font-family: 'Syne', sans-serif; font-size: .58rem;
    letter-spacing: 3px; text-transform: uppercase; color: var(--text-muted);
  }}
  .korcz-footer span {{ color: rgba(229,0,26,.5); }}

  /* ─── SCROLLBAR ─── */
  ::-webkit-scrollbar {{ width: 4px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(229,0,26,.3); border-radius: 2px; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# LOGO + HEADER
# ---------------------------------------------------------------------------
LOGO_PATH = Path(__file__).parent / "logo_spkkorcz.png"

def get_logo_html() -> str:
    try:
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" style="height:54px;opacity:.92;filter:drop-shadow(0 0 10px rgba(229,0,26,.25));">'
    except Exception:
        return '<div style="font-size:2rem;">🚂</div>'

header_c1, header_c2 = st.columns([10, 1])
with header_c1:
    st.markdown(f"""
    <div class="korcz-header">
      {get_logo_html()}
      <div class="korcz-brand">
        <div class="name">KORCZ</div>
        <div class="tagline">System Skanowania Dokumentów Kolejowych</div>
      </div>
      <div class="korcz-header-meta">
        <div class="version-tag">v6.0 &nbsp;·&nbsp; DDU / P3 / Mw 581</div>
        <div class="status-badge">
          <div class="status-dot"></div>
          <span class="status-text">Online</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with header_c2:
    icon = "☀️" if IS_DARK else "🌙"
    label = f"{icon} {'Jasny' if IS_DARK else 'Ciemny'}"
    st.markdown('<div class="btn-theme">', unsafe_allow_html=True)
    if st.button(label, key="theme_toggle"):
        st.session_state.theme = "light" if IS_DARK else "dark"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------------------
ARKUSZ_P3_URL  = st.secrets.get("ARKUSZ_P3_URL",  "https://docs.google.com/spreadsheets/d/1Np2uu4NI7cJ2vYeNuC57ugAQ0wKsvN5gPqUqY745Ikw/edit?usp=sharing")
ARKUSZ_DDU_URL = st.secrets.get("ARKUSZ_DDU_URL", "https://docs.google.com/spreadsheets/d/1lUEohyHvKBwydg9IB3hJQ6pJs0fjptcZHxD-gc4ef-k/edit?usp=sharing")

@st.cache_resource
def get_google_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    return gspread.authorize(creds)


# ===========================================================================
# ROZPOZNANIE TYPU
# ===========================================================================
SLOWA_P3 = [
    "PROTOKÓŁ P6", "PROTOKOL P6",
    "DOPUSZCZENIE DO UŻYTKOWANIA WAGONU TOWAROWEGO",
    "PRZEGLĄD P3", "PRZEGLAD P3",
]
SLOWA_DDU = [
    "MW 581", "Mw 581", "ZAWIADOMIENIE O NAPRAWIE",
    "PO NAPRAWIE POZIOMU P1", "P1/P2",
    "NAPRAWIE WAGONÓW", "NAPRAWIE WAGONOW",
    "PROTOKÓŁ NR", "PROTOKOL NR",
    "ODBIORU WAGONÓW TOWAROWYCH", "ODBIORU WAGONOW TOWAROWYCH",
]

def wykryj_typ(text: str) -> str:
    upper = text.upper()
    for kw in SLOWA_P3:
        if kw.upper() in upper:
            return "P3"
    for kw in SLOWA_DDU:
        if kw.upper() in upper:
            return "DDU"
    if len(_znajdz_wagony_raw(text)) > 1:
        return "DDU"
    return "P3"


# ===========================================================================
# EKSTRAKCJA DANYCH
# ===========================================================================
def formatuj_wagon(cyfry: str) -> str:
    d = re.sub(r"\D", "", cyfry)[:12]
    if len(d) < 12:
        return cyfry
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}"

def _znajdz_wagony_raw(text: str) -> list:
    text_c = re.sub(r"(?m)^\s*\d{1,2}[\.\)\s]\s*", " ", text)
    found, seen = [], set()
    for m in re.finditer(r"\b(\d[\d\s\-\.]{9,16}\d)\b", text_c):
        raw = re.sub(r"\D", "", m.group(1))
        if len(raw) == 12 and raw not in seen:
            if raw[:2] in ("48",) or raw[:3] in ("881", "882", "535", "538"):
                continue
            seen.add(raw)
            found.append(raw)
    return found

def wagon_z_nazwy(fname: str) -> str:
    m = re.search(r"(\d{4})[\s_\-]?(\d{4})[\s_\-]?(\d{3})[\s_\-](\d)", fname)
    if m:
        d = "".join(m.groups())
        return formatuj_wagon(d) if len(d) == 12 else ""
    return ""

def jeden_wagon(text: str) -> str:
    r = _znajdz_wagony_raw(text)
    return formatuj_wagon(r[0]) if r else ""

def wiele_wagonow(text: str) -> list:
    return [formatuj_wagon(r) for r in _znajdz_wagony_raw(text)]

def nr_dop(text: str) -> str:
    m = re.search(r"\bNr[\.\s:]{1,5}([\d\s]{5,14})", text, re.IGNORECASE)
    if m:
        v = re.sub(r"\s", "", m.group(1))
        if 6 <= len(v) <= 12:
            return v
    return ""

def data_doku(text: str) -> str:
    SKIP = r"04[\.\-]05[\.\-]2020"
    for m in re.finditer(r"(\d{1,2})[\.\-](\d{2})[\.\-](\d{2,4})[rRnN\.]?", text):
        if re.search(SKIP, m.group(0)):
            continue
        d, mo, y = m.group(1), m.group(2), m.group(3)
        y = "20" + y if len(y) == 2 else y
        try:
            if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12 and 2020 <= int(y) <= 2035:
                return f"{d.zfill(2)}.{mo}.{y}"
        except ValueError:
            pass
    return ""

ZNANE = [
    "KWK Janina", "KWK Ziemowit", "KWK Piast", "KWK Murcki", "KWK Pniówek",
    "KWK Budryk", "KWK Bielszowice", "KWK Mysłowice", "KWK Bolesław Śmiały",
    "Dwory Terminal", "Terminal Dwory",
    "Elektrownia Jaworzno", "Elektrownia Łagisza", "Elektrownia Siersza",
    "Elektrownia Rybnik", "Elektrownia Połaniec",
]

def lokalizacja(text: str) -> str:
    up = text.upper()
    for lok in ZNANE:
        if lok.upper() in up:
            return lok
    for pat in [
        r"(?:Stacja|Bocznica|Stacja\s*/\s*Bocznica)[\s\.\:\-]{0,5}([^\n\r]{3,50})",
        r"(?:Miejscowo[sś][cć]|Stacja|Warsztat)[\s\.\:\/\-]{0,10}([^\n\r]{3,50})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            k = re.split(r"\s+(?:Data|Numer)\b", m.group(1), flags=re.IGNORECASE)[0].strip().rstrip(".,")
            if len(k) >= 3:
                return k
    m3 = re.search(r"KWK\s+([A-ZŁÓŚĄĆĘŹŻa-ząćęłńóśźż]{2,}(?:\s+[A-Za-ząćęłńóśźż]+)?)", text)
    if m3:
        return ("KWK " + m3.group(1).strip()).title().replace("Kwk", "KWK")
    return ""


# ===========================================================================
# NOWA LOGIKA — OCENIANIE STRON (score-based, nie break-on-first)
# ===========================================================================

# Słownik: słowo_kluczowe → punkty
# Wyższy score = bardziej pasuje do strony DDU/P6
SCORE_P6 = {
    "DOPUSZCZENIE DO UŻYTKOWANIA": 30,
    "DOPUSZCZENIE DO UZYTKOWANIA": 30,
    "PROTOKÓŁ P6":  25,
    "PROTOKOL P6":  25,
    "PRZEGLĄD P3":  20,
    "PRZEGLAD P3":  20,
    " P6 ":         10,
    "WAGONU TOWAROWEGO": 8,
    "DOPUSZCZENIE": 6,
}

# Strony z tymi słowami NIE są stroną P6
SCORE_PENALTY = {
    "ZAWIADOMIENIE O NAPRAWIE": -20,
    "PROTOKÓŁ ODBIORU":         -15,
    "PROTOKOL ODBIORU":         -15,
    "MW 581":                   -15,
    "SPIS WAGONÓW":             -10,
    "SPIS WAGONOW":             -10,
    "LISTA WAGONÓW":            -10,
    "NAPRAWA POZIOMU P":        -8,
    " P2 ":                     -5,
    " P1 ":                     -3,
}

def _score_strony_p6(text: str) -> int:
    """Zwraca wynik dopasowania strony do dokumentu DDU/P6."""
    upper = text.upper()
    score = 0
    for kw, pts in SCORE_P6.items():
        if kw.upper() in upper:
            score += pts
    for kw, pts in SCORE_PENALTY.items():
        if kw.upper() in upper:
            score += pts  # pts są ujemne
    return score


def ocr_z_obrazu(img: Image.Image) -> str:
    """OCR z obiektu PIL Image."""
    img_gray = img.convert("L")
    w, h = img_gray.size
    if w < 2400:
        scale = 2400 / w
        img_gray = img_gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img_gray = ImageEnhance.Contrast(img_gray).enhance(1.9)
    img_gray = ImageEnhance.Sharpness(img_gray).enhance(1.5)
    return pytesseract.image_to_string(img_gray, lang="pol", config="--psm 6 --oem 1")


def _znajdz_strone_p6(doc: fitz.Document) -> int:
    """
    Skanuje WSZYSTKIE strony i wybiera tę z najwyższym score P6.
    Używa 150 DPI dla detekcji (dobry balans jakość/szybkość).
    Fallback: ostatnia strona.
    """
    n = len(doc)
    if n == 1:
        return 0

    najlepszy_idx   = n - 1   # fallback = ostatnia strona
    najlepszy_score = -999

    for i in range(n):
        pix = doc[i].get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes()))
        tekst = pytesseract.image_to_string(img, lang="pol", config="--psm 6 --oem 1")
        score = _score_strony_p6(tekst)

        if score > najlepszy_score:
            najlepszy_score = score
            najlepszy_idx   = i

    return najlepszy_idx


def przetworz_plik(file_bytes: bytes, filename: str, tryb: str = "AUTO") -> list:
    """
    Obsługuje PDF, JPG, PNG.
    Zwraca listę rekordów.
    """
    ext = Path(filename).suffix.lower().lstrip(".")

    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        n_stron = len(doc)

        # Nowa logika — score-based selection
        p6_idx = _znajdz_strone_p6(doc)

        # Podgląd 150 DPI
        pix_prev = doc[p6_idx].get_pixmap(dpi=150)
        podglad  = pix_prev.tobytes("png")

        # OCR 300 DPI
        pix_ocr = doc[p6_idx].get_pixmap(dpi=300)
        img_ocr = Image.open(io.BytesIO(pix_ocr.tobytes()))
        tekst   = ocr_z_obrazu(img_ocr)
        doc.close()

        meta = dict(ddu_strona=p6_idx + 1, n_stron=n_stron)

    else:
        img_raw = Image.open(io.BytesIO(file_bytes))
        img_prev = img_raw.copy()
        if img_prev.width > 1200:
            r = 1200 / img_prev.width
            img_prev = img_prev.resize((1200, int(img_prev.height * r)), Image.LANCZOS)
        buf = io.BytesIO()
        img_prev.convert("RGB").save(buf, format="PNG")
        podglad = buf.getvalue()
        tekst   = ocr_z_obrazu(img_raw)
        meta    = dict(ddu_strona=1, n_stron=1)

    typ = tryb if tryb != "AUTO" else wykryj_typ(tekst)
    dat = data_doku(tekst)
    lok = lokalizacja(tekst)

    base = dict(
        filename=filename, typ=typ, data=dat, lokalizacja=lok,
        podglad_png=podglad, ocr_tekst=tekst,
        wyslano=False, blad="",
        **meta,
    )

    rekordy = []
    if typ == "P3":
        w = wagon_z_nazwy(filename) or jeden_wagon(tekst)
        rekordy.append({**base, "wagon": w, "nr_dop": nr_dop(tekst)})
    else:
        wagony = wiele_wagonow(tekst) or ([wagon_z_nazwy(filename)] if wagon_z_nazwy(filename) else [])
        if wagony:
            for w in wagony:
                rekordy.append({**base, "wagon": w, "nr_dop": ""})
        else:
            rekordy.append({**base, "wagon": "", "nr_dop": "", "blad": "Nie znaleziono wagonów"})

    return rekordy


# ===========================================================================
# SEKCJA 1 — TRYB + UPLOAD
# ===========================================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-header"><span class="ch-accent">◈</span> &nbsp;Wgraj dokumenty</div>', unsafe_allow_html=True)

c1, c2, c3, crest = st.columns([1.1, 0.85, 1.9, 4])
with c1:
    if st.button("🔍 AUTO", use_container_width=True,
                 type="primary" if st.session_state.tryb == "AUTO" else "secondary"):
        st.session_state.tryb = "AUTO"; st.rerun()
with c2:
    if st.button("📋 P3", use_container_width=True,
                 type="primary" if st.session_state.tryb == "P3" else "secondary"):
        st.session_state.tryb = "P3"; st.rerun()
with c3:
    if st.button("🔧 DDU / P1·P2 / Mw 581", use_container_width=True,
                 type="primary" if st.session_state.tryb == "DDU" else "secondary"):
        st.session_state.tryb = "DDU"; st.rerun()

TRYB_INFO = {
    "AUTO": ("🔍", "#7090ee", "Automatyczne wykrywanie — program sam rozpozna typ dokumentu na podstawie treści."),
    "P3":   ("📋", "#7090ee", "Tryb Przegląd P3 — jeden wagon na plik, zapis do arkusza P3."),
    "DDU":  ("🔧", "#e5001a", "Tryb DDU / Mw 581 / P1·P2 — wyciąga wszystkie wagony z tabeli, zapis do arkusza DDU."),
}
ic, col, opis = TRYB_INFO[st.session_state.tryb]
st.markdown(
    f'<div class="info-box"><span>{ic}</span>'
    f'<span style="color:{col};font-family:Syne,sans-serif;font-weight:700;font-size:.72rem;letter-spacing:2px">TRYB {st.session_state.tryb}</span>'
    f'&nbsp;&nbsp;<span>{opis}</span></div>',
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Przeciągnij pliki lub kliknij — PDF, JPG, PNG",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

# ---- Przetwarzanie ----
if uploaded_files:
    przetworzone = {w["filename"] for w in st.session_state.wyniki}
    nowe = [f for f in uploaded_files if f.name not in przetworzone]

    if nowe:
        prog_bar = st.progress(0, text="Inicjalizacja…")
        for i, plik in enumerate(nowe):
            prog_bar.progress(i / len(nowe), text=f"⚙️  OCR: {plik.name}  ({i+1}/{len(nowe)})")
            try:
                rekordy = przetworz_plik(plik.read(), plik.name, st.session_state.tryb)
                st.session_state.wyniki.extend(rekordy)
            except Exception as e:
                st.session_state.wyniki.append(dict(
                    filename=plik.name, typ="?", wagon="", nr_dop="", data="", lokalizacja="",
                    ddu_strona=0, n_stron=0, podglad_png=None, ocr_tekst="",
                    wyslano=False, blad=str(e),
                ))
        prog_bar.progress(1.0, text="✅  Gotowe!")
        time.sleep(0.5)
        prog_bar.empty()
        st.rerun()


# ===========================================================================
# SEKCJA 2 — DASHBOARD + TABELA
# ===========================================================================
wyniki = st.session_state.wyniki

if wyniki:
    n_p3   = sum(1 for w in wyniki if w["typ"] == "P3")
    n_ddu  = sum(1 for w in wyniki if w["typ"] == "DDU")
    n_ok   = sum(1 for w in wyniki if w["wagon"] and not w["blad"])
    n_prob = sum(1 for w in wyniki if not w["wagon"] or w["blad"])
    n_wys  = sum(1 for w in wyniki if w["wyslano"])

    mc = st.columns(6)
    mc[0].metric("Rekordów",  len(wyniki))
    mc[1].metric("Typ P3",    n_p3)
    mc[2].metric("Typ DDU",   n_ddu)
    mc[3].metric("Gotowe",    n_ok)
    mc[4].metric("Korekta",   n_prob)
    mc[5].metric("Wysłano",   n_wys)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="ch-accent">◈</span> &nbsp;Wyniki skanowania</div>', unsafe_allow_html=True)

    hc = st.columns([0.3, 1.8, 0.6, 1.5, 0.95, 1.55, 1.0, 0.8, 0.6])
    for col, h in zip(hc, ["#", "Plik", "Typ", "Nr wagonu", "Nr dop.", "Lokalizacja", "Data", "Status", ""]):
        col.markdown(f'<div class="tbl-head">{h}</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    for idx, w in enumerate(wyniki):
        rc = st.columns([0.3, 1.8, 0.6, 1.5, 0.95, 1.55, 1.0, 0.8, 0.6])
        rc[0].markdown(f'<div class="tbl-num" style="padding-top:8px">{idx+1}</div>', unsafe_allow_html=True)
        bar = "type-bar-p3" if w["typ"] == "P3" else "type-bar-ddu"
        rc[1].markdown(f'<div class="{bar} tbl-file" style="padding-top:6px">{w["filename"]}</div>', unsafe_allow_html=True)
        tb = '<span class="badge badge-p3">P3</span>' if w["typ"] == "P3" else '<span class="badge badge-ddu">DDU</span>'
        rc[2].markdown(f'<div style="padding-top:6px">{tb}</div>', unsafe_allow_html=True)
        rc[3].markdown(f'<div class="wagon-num" style="padding-top:6px">{w["wagon"] or "—"}</div>', unsafe_allow_html=True)
        rc[4].markdown(f'<div class="tbl-meta" style="padding-top:8px">{w["nr_dop"] or "—"}</div>', unsafe_allow_html=True)
        rc[5].markdown(f'<div class="tbl-meta-hi" style="padding-top:8px">{w["lokalizacja"] or "—"}</div>', unsafe_allow_html=True)
        rc[6].markdown(f'<div class="tbl-meta" style="padding-top:8px">{w["data"] or "—"}</div>', unsafe_allow_html=True)
        if w["blad"]:      sb = '<span class="badge badge-error">Błąd</span>'
        elif w["wyslano"]: sb = '<span class="badge badge-sent">Wysłano</span>'
        elif w["wagon"]:   sb = '<span class="badge badge-ok">OK</span>'
        else:              sb = '<span class="badge badge-warn">Korekta</span>'
        rc[7].markdown(f'<div style="padding-top:6px">{sb}</div>', unsafe_allow_html=True)
        with rc[8]:
            if st.button("✏️", key=f"e{idx}", help="Edytuj / wyślij"):
                st.session_state.edytowany_idx = idx
        st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- BATCH WYŚLIJ ----
    gp3  = [(i, w) for i, w in enumerate(wyniki) if w["wagon"] and not w["wyslano"] and not w["blad"] and w["typ"] == "P3"]
    gddu = [(i, w) for i, w in enumerate(wyniki) if w["wagon"] and not w["wyslano"] and not w["blad"] and w["typ"] == "DDU"]

    if gp3 or gddu:
        st.markdown("<br>", unsafe_allow_html=True)
        cs, cc = st.columns([4, 1])
        with cs:
            parts = []
            if gp3:  parts.append(f"{len(gp3)} × P3")
            if gddu: parts.append(f"{len(gddu)} × DDU")
            lbl = "  +  ".join(parts)
            st.markdown('<div class="btn-send">', unsafe_allow_html=True)
            if st.button(f"🚀  WYŚLIJ DO GOOGLE SHEETS  ·  {lbl}", type="primary", use_container_width=True):
                try:
                    client = get_google_client()
                    n_ok_p3, n_ok_ddu = 0, 0
                    if gp3 and ARKUSZ_P3_URL:
                        sh = client.open_by_url(ARKUSZ_P3_URL).sheet1
                        lp = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                        rows = []
                        for off, (i, w) in enumerate(gp3):
                            rows.append([lp+off, w["nr_dop"], w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sh.append_rows(rows)
                        n_ok_p3 = len(rows)
                    if gddu and ARKUSZ_DDU_URL:
                        sh = client.open_by_url(ARKUSZ_DDU_URL).sheet1
                        lp = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                        rows = []
                        for off, (i, w) in enumerate(gddu):
                            rows.append([lp+off, w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sh.append_rows(rows)
                        n_ok_ddu = len(rows)
                    st.success(f"✅  Zapisano {n_ok_p3} wpisów P3 i {n_ok_ddu} wpisów DDU.")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌  Błąd Google Sheets: {e}")
            st.markdown('</div>', unsafe_allow_html=True)
        with cc:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("🗑  Wyczyść", use_container_width=True):
                st.session_state.wyniki = []
                st.session_state.edytowany_idx = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ===========================================================================
# SEKCJA 3 — PANEL EDYCJI
# ===========================================================================
if st.session_state.edytowany_idx is not None and wyniki:
    idx = st.session_state.edytowany_idx
    if idx < len(wyniki):
        w = wyniki[idx]
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="card"><div class="card-header">'
            f'<span class="ch-accent">◈</span> &nbsp;Edycja #{idx+1}'
            f'<span style="font-size:.6rem;color:var(--text-muted);margin-left:14px">{w["filename"]}</span>'
            f'</div>', unsafe_allow_html=True,
        )
        col_img, _, col_form = st.columns([5, 0.1, 4])
        with col_img:
            st.markdown('<div class="edit-lbl">Podgląd dokumentu</div>', unsafe_allow_html=True)
            if w["podglad_png"]:
                st.image(w["podglad_png"], use_container_width=True)
                st.caption(f'Strona {w.get("ddu_strona","?")} / {w.get("n_stron","?")}')
            else:
                st.warning("Brak podglądu.")
            with st.expander("🔍 Surowy tekst OCR"):
                st.code(w.get("ocr_tekst", "(brak)"), language=None)
        with col_form:
            st.markdown('<div class="edit-lbl">Dane do rejestru</div>', unsafe_allow_html=True)
            new_typ = st.selectbox("Typ dokumentu", ["P3", "DDU"],
                                   index=0 if w["typ"] == "P3" else 1, key=f"sel_{idx}")
            wagon_v = st.text_input("Numer wagonu  ✱", value=w["wagon"],
                                    placeholder="np.  3351 6666 408-6", key=f"wg_{idx}")
            nrdop_v = ""
            if new_typ == "P3":
                nrdop_v = st.text_input("Numer dopuszczenia", value=w["nr_dop"],
                                        placeholder="np.  17044086", key=f"nd_{idx}")
            data_v = st.text_input("Data wystawienia", value=w["data"],
                                   placeholder="DD.MM.RRRR", key=f"dt_{idx}")
            lok_v  = st.text_input("Miejscowość / Zakład", value=w["lokalizacja"],
                                   placeholder="np.  KWK Janina", key=f"lk_{idx}")
            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([2, 2, 1])
            with b1:
                if st.button("💾  Zapisz", key=f"sv_{idx}", use_container_width=True):
                    st.session_state.wyniki[idx].update(
                        typ=new_typ, wagon=wagon_v, nr_dop=nrdop_v,
                        data=data_v, lokalizacja=lok_v, blad="")
                    st.success("Zapisano.")
            with b2:
                if st.button("✅  Wyślij wpis", key=f"sn_{idx}",
                             use_container_width=True, type="primary"):
                    if not wagon_v.strip():
                        st.error("❌  Numer wagonu jest wymagany.")
                    else:
                        try:
                            client = get_google_client()
                            url = ARKUSZ_P3_URL if new_typ == "P3" else ARKUSZ_DDU_URL
                            sh = client.open_by_url(url).sheet1
                            lp = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                            row = ([lp, nrdop_v, lok_v, data_v, wagon_v.strip()] if new_typ == "P3"
                                   else [lp, lok_v, data_v, wagon_v.strip()])
                            sh.append_rows([row])
                            st.session_state.wyniki[idx].update(
                                typ=new_typ, wagon=wagon_v, nr_dop=nrdop_v,
                                data=data_v, lokalizacja=lok_v, wyslano=True, blad="")
                            st.success(f"✅  LP={lp} → {new_typ}")
                            st.balloons()
                            st.session_state.edytowany_idx = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌  {e}")
            with b3:
                st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
                if st.button("✖", key=f"cl_{idx}", use_container_width=True):
                    st.session_state.edytowany_idx = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ===========================================================================
# STOPKA
# ===========================================================================
st.markdown("""
<div class="korcz-footer">
  KORCZ Serwis Pojazdów Kolejowych &nbsp;·&nbsp; v6.0
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <span>P3 → Arkusz Przeglądów</span>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <span>DDU / Mw 581 / P1·P2 → Arkusz DDU</span>
</div>
""", unsafe_allow_html=True)
