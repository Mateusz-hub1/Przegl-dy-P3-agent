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
import cv2
import numpy as np

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
# STYL CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Barlow:wght@400;500;600&display=swap');

  /* ── GLOBAL ── */
  .stApp { background-color: #0c0c0c; font-family: 'Barlow', sans-serif; }
  header[data-testid="stHeader"] { background: transparent !important; }
  #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
  section[data-testid="stSidebar"] { display: none; }

  /* ── HEADER ── */
  .korcz-header {
    display: flex; align-items: center; gap: 28px;
    padding: 24px 0 20px 0;
    border-bottom: 3px solid #e5001a;
    margin-bottom: 36px;
  }
  .korcz-logo-text { font-family: 'Barlow Condensed', sans-serif; }
  .korcz-logo-text .brand {
    font-size: 2.8rem; font-weight: 900; color: #e5001a;
    letter-spacing: 3px; line-height: 1;
  }
  .korcz-logo-text .sub {
    font-size: .85rem; font-weight: 600; color: #555;
    letter-spacing: 4px; text-transform: uppercase; margin-top: 2px;
  }
  .korcz-header-right {
    margin-left: auto;
    text-align: right;
    font-family: 'Barlow Condensed', sans-serif;
  }
  .korcz-header-right .ver { font-size: .7rem; color: #444; letter-spacing: 3px; text-transform: uppercase; }
  .korcz-header-right .status-dot {
    display: inline-block; width: 8px; height: 8px;
    background: #00d455; border-radius: 50%; margin-right: 6px;
    box-shadow: 0 0 6px #00d455;
  }
  .korcz-header-right .status-txt { font-size: .75rem; color: #00d455; letter-spacing: 2px; }

  /* ── KARTY ── */
  .card {
    background: #161616;
    border: 1px solid #252525;
    border-radius: 6px;
    padding: 22px 26px;
    margin-bottom: 18px;
  }
  .card-header {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem; font-weight: 700;
    color: #e5001a; letter-spacing: 3px; text-transform: uppercase;
    margin-bottom: 16px; padding-bottom: 10px;
    border-bottom: 1px solid #222;
    display: flex; align-items: center; gap: 10px;
  }
  .card-header .ch-icon { font-size: 1.1rem; }

  /* ── TRYB SWITCHER ── */
  .mode-bar {
    display: flex; gap: 8px; margin-bottom: 18px;
  }
  .mode-pill {
    padding: 8px 20px; border-radius: 20px; cursor: pointer;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: .9rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; border: 1px solid #333;
    background: #111; color: #555; transition: all .2s;
    white-space: nowrap;
  }
  .mode-pill:hover { border-color: #666; color: #aaa; }
  .mode-pill.active-auto  { background: #1a1a2e; border-color: #5599ff; color: #5599ff; }
  .mode-pill.active-p3    { background: #001830; border-color: #5599ff; color: #88bbff; }
  .mode-pill.active-ddu   { background: #1a0005; border-color: #e5001a; color: #ff6677; }

  /* ── DROP ZONE ── */
  [data-testid="stFileUploader"] {
    background: #0f0f0f !important;
    border: 2px dashed #2a2a2a !important;
    border-radius: 8px !important;
    padding: 32px !important;
    transition: border-color .25s, background .25s;
  }
  [data-testid="stFileUploader"]:hover {
    border-color: #e5001a !important;
    background: #160005 !important;
  }
  [data-testid="stFileUploaderDropzone"] p { color: #555 !important; }

  /* ── METRYKI ── */
  [data-testid="stMetric"] {
    background: #111 !important;
    border: 1px solid #222 !important;
    border-radius: 6px !important;
    padding: 18px 20px !important;
    position: relative;
    overflow: hidden;
  }
  [data-testid="stMetric"]::before {
    content: ''; position: absolute;
    top: 0; left: 0; width: 3px; height: 100%;
    background: #e5001a;
  }
  [data-testid="stMetricLabel"] {
    color: #555 !important;
    font-size: .68rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    font-family: 'Barlow Condensed', sans-serif !important;
  }
  [data-testid="stMetricValue"] {
    color: #fff !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 2.2rem !important;
    font-weight: 900 !important;
  }

  /* ── BADGES ── */
  .badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 3px;
    font-size: .7rem; font-weight: 700;
    font-family: 'Barlow Condensed', sans-serif;
    letter-spacing: 1px; text-transform: uppercase;
  }
  .badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
  .badge-ok    { background: #021a0c; color: #00d455; border: 1px solid #004d1a; }
  .badge-ok::before { background: #00d455; }
  .badge-warn  { background: #1a1000; color: #ffa500; border: 1px solid #4d3000; }
  .badge-warn::before { background: #ffa500; }
  .badge-error { background: #1a0005; color: #ff4060; border: 1px solid #4d0010; }
  .badge-error::before { background: #ff4060; }
  .badge-sent  { background: #001a3d; color: #4090ff; border: 1px solid #004d99; }
  .badge-sent::before { background: #4090ff; }
  .badge-p3    { background: #001225; color: #5599ff; border: 1px solid #003366; }
  .badge-p3::before { background: #5599ff; }
  .badge-ddu   { background: #1a0005; color: #ff7088; border: 1px solid #4d0015; }
  .badge-ddu::before { background: #ff7088; }

  /* ── TABELA ── */
  .tbl-row {
    display: grid;
    grid-template-columns: 32px 1fr 72px 160px 90px 160px 100px 80px 48px;
    align-items: center; gap: 0 12px;
    padding: 10px 4px;
    border-bottom: 1px solid #1a1a1a;
    transition: background .15s;
  }
  .tbl-row:hover { background: #161616; }
  .tbl-head { color: #3a3a3a !important; font-size: .65rem !important; letter-spacing: 2px; text-transform: uppercase; font-family: 'Barlow Condensed', sans-serif; }
  .tbl-num  { color: #333; font-size: .85rem; }
  .tbl-file { color: #777; font-size: .78rem; word-break: break-all; line-height: 1.3; }
  .type-bar-p3  { border-left: 3px solid #5599ff; padding-left: 8px; }
  .type-bar-ddu { border-left: 3px solid #e5001a; padding-left: 8px; }
  .wagon-num { font-family: 'Barlow Condensed', sans-serif; font-size: 1rem; color: #eee; font-weight: 700; letter-spacing: 1px; }
  .tbl-meta { color: #555; font-size: .8rem; }
  .tbl-meta-hi { color: #888; font-size: .8rem; }

  /* ── INPUTS ── */
  .stTextInput > label {
    color: #555 !important; font-size: .7rem !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-family: 'Barlow Condensed', sans-serif !important;
  }
  .stTextInput > div > div > input {
    background: #0f0f0f !important; border: 1px solid #2a2a2a !important;
    color: #eee !important; border-radius: 4px !important;
    font-family: 'Barlow', sans-serif !important; font-size: .95rem !important;
    padding: 10px 14px !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #e5001a !important;
    box-shadow: 0 0 0 2px rgba(229,0,26,.15) !important;
  }
  .stSelectbox > label { color: #555 !important; font-size: .7rem !important; letter-spacing: 2px !important; text-transform: uppercase !important; }
  .stSelectbox > div > div { background: #0f0f0f !important; border: 1px solid #2a2a2a !important; color: #eee !important; border-radius: 4px !important; }

  /* ── PRZYCISKI ── */
  .stButton > button {
    background: #e5001a !important; color: #fff !important;
    border: none !important; border-radius: 4px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: .95rem !important; font-weight: 700 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    padding: 11px 22px !important;
    transition: background .15s, transform .1s !important;
  }
  .stButton > button:hover { background: #c00018 !important; transform: translateY(-1px) !important; }
  .stButton > button:active { transform: translateY(0) !important; }
  .btn-ghost > button {
    background: transparent !important;
    border: 1px solid #2a2a2a !important;
    color: #555 !important;
  }
  .btn-ghost > button:hover { border-color: #555 !important; color: #aaa !important; background: transparent !important; }

  /* ── PROGRESS ── */
  .stProgress > div > div > div { background: linear-gradient(90deg, #e5001a, #ff4060) !important; border-radius: 2px !important; }

  /* ── EXPANDER ── */
  .streamlit-expanderHeader {
    background: #0f0f0f !important; color: #444 !important;
    font-size: .78rem !important; border-radius: 4px !important;
    border: 1px solid #1e1e1e !important;
  }
  .streamlit-expanderContent { background: #0a0a0a !important; }

  /* ── ALERTS ── */
  .stAlert { border-radius: 4px !important; }
  [data-baseweb="notification"] { background: #0f1a0a !important; border-left: 3px solid #00d455 !important; }

  /* ── SEPARATOR ── */
  hr { border: none !important; border-top: 1px solid #1a1a1a !important; margin: 8px 0 !important; }

  /* ── TOAST / info box ── */
  .info-box {
    background: #111; border: 1px solid #252525; border-radius: 6px;
    padding: 14px 18px; margin: 12px 0;
    display: flex; align-items: center; gap: 12px;
    font-size: .85rem; color: #666;
  }
  .info-box .ib-icon { font-size: 1.1rem; }
  .info-box strong { color: #aaa; }

  /* ── STOPKA ── */
  .korcz-footer {
    text-align: center; margin-top: 48px; padding-top: 20px;
    border-top: 1px solid #1a1a1a;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: .65rem; letter-spacing: 3px; text-transform: uppercase;
    color: #2a2a2a;
  }
  .korcz-footer span { color: #333; }
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
        return f'<img src="data:image/png;base64,{b64}" style="height:60px;filter:brightness(1.05);">'
    except Exception:
        return '<div style="font-size:2.5rem;">🚂</div>'


st.markdown(f"""
<div class="korcz-header">
  {get_logo_html()}
  <div class="korcz-logo-text">
    <div class="brand">KORCZ</div>
    <div class="sub">System Skanowania Dokumentów Kolejowych</div>
  </div>
  <div class="korcz-header-right">
    <div class="ver">v4.5 &nbsp;·&nbsp; OpenCV + DDU / P3</div>
    <div style="margin-top:6px">
      <span class="status-dot"></span>
      <span class="status-txt">System aktywny</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------------------
ARKUSZ_P3_URL = "https://docs.google.com/spreadsheets/d/1Np2uu4NI7cJ2vYeNuC57ugAQ0wKsvN5gPqUqY745Ikw/edit?usp=sharing"
ARKUSZ_DDU_URL = "https://docs.google.com/spreadsheets/d/1lUEohyHvKBwydg9IB3hJQ6pJs0fjptcZHxD-gc4ef-k/edit?usp=sharing"


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
    "PROTOKÓŁ P6", "PROTOKOL P6", "DOPUSZCZENIE DO UŻYTKOWANIA WAGONU TOWAROWEGO",
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
    # 1. Agresywna korekta najczęstszych błędów OCR w obrębie ciągów alfanumerycznych
    text_c = text.replace("O", "0").replace("Q", "0")
    text_c = text_c.replace("S", "5").replace("s", "5")
    text_c = text_c.replace("l", "1").replace("I", "1").replace("!", "1")
    text_c = text_c.replace("B", "8")

    text_c = re.sub(r"(?m)^\s*\d{1,2}[\.\)\s]\s*", " ", text_c)
    found, seen = [], set()

    # 2. Tolerancja na luźne spacje i tabulacje w Tesserakcie
    for m in re.finditer(r"\b(\d[\d\s\t\n\-\.]{9,20}\d)\b", text_c):
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
# OBSŁUGA PLIKÓW — OpenCV + Tesseract
# ===========================================================================
SUPPORTED_TYPES = ["pdf", "jpg", "jpeg", "png"]


def ocr_z_obrazu(img: Image.Image) -> str:
    """Wzmocniony OCR z użyciem OpenCV. Idealny dla zaszumionych zdjęć."""
    img_gray = img.convert("L")

    w, h = img_gray.size
    if w < 2800:
        scale = 2800 / w
        img_gray = img_gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    open_cv_image = np.array(img_gray)
    blurred = cv2.GaussianBlur(open_cv_image, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 21, 15
    )
    final_img = Image.fromarray(binary)

    return pytesseract.image_to_string(final_img, lang="pol", config="--psm 4 --oem 1")


def przetworz_plik(file_bytes: bytes, filename: str, tryb: str = "AUTO") -> list:
    ext = Path(filename).suffix.lower().lstrip(".")

    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        n_stron = len(doc)
        ddu_idx = len(doc) - 1

        if n_stron > 1:
            for i in range(n_stron - 1, max(n_stron - 9, -1), -1):
                pix = doc[i].get_pixmap(dpi=100)
                img_q = Image.open(io.BytesIO(pix.tobytes()))
                t = pytesseract.image_to_string(img_q, lang="pol").upper()
                if "DOPUSZCZENIE" in t or ("PROTOKÓŁ" in t and "P6" in t):
                    ddu_idx = i
                    break

        pix_prev = doc[ddu_idx].get_pixmap(dpi=150)
        podglad = pix_prev.tobytes("png")

        # Zwiększone DPI (z 300 na 400) dla lepszego detalu przed OpenCV
        pix_ocr = doc[ddu_idx].get_pixmap(dpi=400)
        img_ocr = Image.open(io.BytesIO(pix_ocr.tobytes()))
        tekst = ocr_z_obrazu(img_ocr)
        doc.close()

        meta = dict(ddu_strona=ddu_idx + 1, n_stron=n_stron)

    else:
        img_raw = Image.open(io.BytesIO(file_bytes))
        img_prev = img_raw.copy()
        if img_prev.width > 1200:
            r = 1200 / img_prev.width
            img_prev = img_prev.resize((1200, int(img_prev.height * r)), Image.LANCZOS)

        with io.BytesIO() as buf:
            img_prev.convert("RGB").save(buf, format="PNG")
            podglad = buf.getvalue()

        tekst = ocr_z_obrazu(img_raw)
        meta = dict(ddu_strona=1, n_stron=1)

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
# SESSION STATE
# ===========================================================================
if "wyniki" not in st.session_state: st.session_state.wyniki = []
if "edytowany_idx" not in st.session_state: st.session_state.edytowany_idx = None
if "tryb" not in st.session_state: st.session_state.tryb = "AUTO"

# ===========================================================================
# SEKCJA 1 — TRYB + UPLOAD
# ===========================================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-header"><span class="ch-icon">📂</span> Wgraj dokumenty</div>', unsafe_allow_html=True)

c1, c2, c3, crest = st.columns([1.1, 0.85, 1.9, 4])
with c1:
    if st.button("🔍 AUTO", use_container_width=True,
                 type="primary" if st.session_state.tryb == "AUTO" else "secondary"):
        st.session_state.tryb = "AUTO";
        st.rerun()
with c2:
    if st.button("📋 P3", use_container_width=True, type="primary" if st.session_state.tryb == "P3" else "secondary"):
        st.session_state.tryb = "P3";
        st.rerun()
with c3:
    if st.button("🔧 DDU / P1·P2 / Mw 581", use_container_width=True,
                 type="primary" if st.session_state.tryb == "DDU" else "secondary"):
        st.session_state.tryb = "DDU";
        st.rerun()

TRYB_INFO = {
    "AUTO": ("🔍", "#5599ff", "Automatyczne wykrywanie — program sam rozpozna typ dokumentu na podstawie treści."),
    "P3": ("📋", "#5599ff", "Tryb Przegląd P3 — jeden wagon na plik, zapis do arkusza P3."),
    "DDU": ("🔧", "#e5001a", "Tryb DDU / Mw 581 / P1·P2 — wyciąga wszystkie wagony z tabeli, zapis do arkusza DDU."),
}
ic, col, opis = TRYB_INFO[st.session_state.tryb]
st.markdown(
    f'<div class="info-box"><span class="ib-icon">{ic}</span><span style="color:{col}"><strong>Tryb {st.session_state.tryb}:</strong></span>&nbsp;{opis}</div>',
    unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Przeciągnij pliki lub kliknij — PDF, JPG, PNG",
    type=SUPPORTED_TYPES,
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_files:
    przetworzone = {w["filename"] for w in st.session_state.wyniki}
    nowe = [f for f in uploaded_files if f.name not in przetworzone]

    if nowe:
        prog_bar = st.progress(0, text="Inicjalizacja…")
        for i, plik in enumerate(nowe):
            prog_bar.progress((i) / len(nowe), text=f"⚙️ OCR + OpenCV: {plik.name}  ({i + 1}/{len(nowe)})")
            try:
                rekordy = przetworz_plik(plik.read(), plik.name, st.session_state.tryb)
                st.session_state.wyniki.extend(rekordy)
            except Exception as e:
                st.session_state.wyniki.append(dict(
                    filename=plik.name, typ="?", wagon="", nr_dop="", data="", lokalizacja="",
                    ddu_strona=0, n_stron=0, podglad_png=None, ocr_tekst="",
                    wyslano=False, blad=str(e),
                ))
            time.sleep(0.03)

        prog_bar.progress(1.0, text="✅ Gotowe!")
        time.sleep(0.6)
        prog_bar.empty()
        st.rerun()

# ===========================================================================
# SEKCJA 2 — DASHBOARD + TABELA
# ===========================================================================
wyniki = st.session_state.wyniki

if wyniki:
    n_p3 = sum(1 for w in wyniki if w["typ"] == "P3")
    n_ddu = sum(1 for w in wyniki if w["typ"] == "DDU")
    n_ok = sum(1 for w in wyniki if w["wagon"] and not w["blad"])
    n_prob = sum(1 for w in wyniki if not w["wagon"] or w["blad"])
    n_wys = sum(1 for w in wyniki if w["wyslano"])

    mc = st.columns(6)
    mc[0].metric("Rekordów", len(wyniki))
    mc[1].metric("Typ P3", n_p3)
    mc[2].metric("Typ DDU", n_ddu)
    mc[3].metric("Gotowe", n_ok)
    mc[4].metric("Korekta", n_prob)
    mc[5].metric("Wysłano", n_wys)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="ch-icon">📋</span> Wyniki skanowania</div>',
                unsafe_allow_html=True)

    hc = st.columns([0.3, 1.8, 0.6, 1.5, 0.95, 1.55, 1.0, 0.8, 0.6])
    for col, h in zip(hc, ["#", "Plik", "Typ", "Nr wagonu", "Nr dop.", "Lokalizacja", "Data", "Status", ""]):
        col.markdown(f'<div class="tbl-head">{h}</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    for idx, w in enumerate(wyniki):
        rc = st.columns([0.3, 1.8, 0.6, 1.5, 0.95, 1.55, 1.0, 0.8, 0.6])

        rc[0].markdown(f'<div class="tbl-num" style="padding-top:8px">{idx + 1}</div>', unsafe_allow_html=True)

        bar = "type-bar-p3" if w["typ"] == "P3" else "type-bar-ddu"
        rc[1].markdown(f'<div class="{bar} tbl-file" style="padding-top:6px">{w["filename"]}</div>',
                       unsafe_allow_html=True)

        tb = '<span class="badge badge-p3">P3</span>' if w[
                                                             "typ"] == "P3" else '<span class="badge badge-ddu">DDU</span>'
        rc[2].markdown(f'<div style="padding-top:6px">{tb}</div>', unsafe_allow_html=True)

        rc[3].markdown(f'<div class="wagon-num" style="padding-top:6px">{w["wagon"] or "—"}</div>',
                       unsafe_allow_html=True)
        rc[4].markdown(f'<div class="tbl-meta" style="padding-top:8px">{w["nr_dop"] or "—"}</div>',
                       unsafe_allow_html=True)
        rc[5].markdown(f'<div class="tbl-meta-hi" style="padding-top:8px">{w["lokalizacja"] or "—"}</div>',
                       unsafe_allow_html=True)
        rc[6].markdown(f'<div class="tbl-meta" style="padding-top:8px">{w["data"] or "—"}</div>',
                       unsafe_allow_html=True)

        if w["blad"]:
            sb = '<span class="badge badge-error">Błąd</span>'
        elif w["wyslano"]:
            sb = '<span class="badge badge-sent">Wysłano</span>'
        elif w["wagon"]:
            sb = '<span class="badge badge-ok">OK</span>'
        else:
            sb = '<span class="badge badge-warn">Korekta</span>'
        rc[7].markdown(f'<div style="padding-top:6px">{sb}</div>', unsafe_allow_html=True)

        with rc[8]:
            if st.button("✏️", key=f"e{idx}", help="Edytuj / wyślij"):
                st.session_state.edytowany_idx = idx

        st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    gp3 = [(i, w) for i, w in enumerate(wyniki) if
           w["wagon"] and not w["wyslano"] and not w["blad"] and w["typ"] == "P3"]
    gddu = [(i, w) for i, w in enumerate(wyniki) if
            w["wagon"] and not w["wyslano"] and not w["blad"] and w["typ"] == "DDU"]

    if gp3 or gddu:
        st.markdown("<br>", unsafe_allow_html=True)
        cs, cc = st.columns([4, 1])

        with cs:
            parts = []
            if gp3:  parts.append(f"{len(gp3)} × P3")
            if gddu: parts.append(f"{len(gddu)} × DDU")
            lbl = "  +  ".join(parts)

            if st.button(f"🚀  WYŚLIJ DO GOOGLE SHEETS  ·  {lbl}", type="primary", use_container_width=True):
                try:
                    client = get_google_client()
                    n_ok_p3, n_ok_ddu = 0, 0

                    if gp3 and ARKUSZ_P3_URL:
                        sh = client.open_by_url(ARKUSZ_P3_URL).sheet1
                        lp = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                        rows = []
                        for off, (i, w) in enumerate(gp3):
                            rows.append([lp + off, w["nr_dop"], w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sh.append_rows(rows)
                        n_ok_p3 = len(rows)

                    if gddu and ARKUSZ_DDU_URL:
                        sh = client.open_by_url(ARKUSZ_DDU_URL).sheet1
                        lp = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                        rows = []
                        for off, (i, w) in enumerate(gddu):
                            rows.append([lp + off, w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sh.append_rows(rows)
                        n_ok_ddu = len(rows)

                    st.success(f"✅ Zapisano {n_ok_p3} wpisów P3 i {n_ok_ddu} wpisów DDU do Google Sheets.")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Błąd połączenia z Google Sheets: {e}")

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
            f'<span class="ch-icon">✏️</span> Edycja rekordu #{idx + 1}'
            f'<span style="font-size:.7rem;color:#333;margin-left:12px">{w["filename"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_img, col_sep, col_form = st.columns([5, 0.1, 4])

        with col_img:
            st.markdown(
                '<div class="section-label" style="color:#333;font-size:.65rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Podgląd dokumentu</div>',
                unsafe_allow_html=True)
            if w["podglad_png"]:
                st.image(w["podglad_png"], use_container_width=True)
                st.caption(f'Strona {w.get("ddu_strona", "?")} z {w.get("n_stron", "?")}')
            else:
                st.warning("Brak podglądu — błąd przetwarzania pliku.")
            with st.expander("🔍 Surowy tekst OCR (diagnostyka)"):
                st.code(w.get("ocr_tekst", "(brak)"), language=None)

        with col_form:
            st.markdown(
                '<div style="color:#333;font-size:.65rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px">Dane do rejestru</div>',
                unsafe_allow_html=True)

            new_typ = st.selectbox(
                "Typ dokumentu",
                ["P3", "DDU"],
                index=0 if w["typ"] == "P3" else 1,
                key=f"sel_{idx}",
            )
            wagon_v = st.text_input(
                "Numer wagonu  ✱",
                value=w["wagon"],
                placeholder="np.  3351 6666 408-6",
                key=f"wg_{idx}",
            )
            nrdop_v = ""
            if new_typ == "P3":
                nrdop_v = st.text_input(
                    "Numer dopuszczenia",
                    value=w["nr_dop"],
                    placeholder="np.  17044086",
                    key=f"nd_{idx}",
                )
            data_v = st.text_input(
                "Data wystawienia",
                value=w["data"],
                placeholder="DD.MM.RRRR",
                key=f"dt_{idx}",
            )
            lok_v = st.text_input(
                "Miejscowość / Zakład",
                value=w["lokalizacja"],
                placeholder="np.  KWK Janina",
                key=f"lk_{idx}",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([2, 2, 1])

            with b1:
                if st.button("💾  Zapisz zmiany", key=f"sv_{idx}", use_container_width=True):
                    st.session_state.wyniki[idx].update(
                        typ=new_typ, wagon=wagon_v, nr_dop=nrdop_v,
                        data=data_v, lokalizacja=lok_v, blad="",
                    )
                    st.success("Zmiany zapisane.")

            with b2:
                if st.button("✅  Wyślij ten wpis", key=f"sn_{idx}",
                             use_container_width=True, type="primary"):
                    if not wagon_v.strip():
                        st.error("❌ Numer wagonu jest wymagany.")
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
                                data=data_v, lokalizacja=lok_v, wyslano=True, blad="",
                            )
                            st.success(f"✅ LP={lp} → arkusz {new_typ}")
                            st.balloons()
                            st.session_state.edytowany_idx = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")

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
  KORCZ Serwis Pojazdów Kolejowych &nbsp;·&nbsp; v4.5 &nbsp;·&nbsp; OpenCV Enhanced
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <span>P3 → Arkusz Przeglądów</span>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <span>DDU / Mw 581 / P1·P2 → Arkusz DDU</span>
</div>
""", unsafe_allow_html=True)
