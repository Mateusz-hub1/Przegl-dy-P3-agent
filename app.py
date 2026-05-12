# ===========================================================================
#  KORCZ — Skaner DDU / P3  v5.0
#  OCR: EasyOCR (zastąpił Tesseract)
#  Obsługuje: PDF, JPG, JPEG, PNG
# ===========================================================================

import streamlit as st
import fitz           # PyMuPDF
import easyocr
import numpy as np
from PIL import Image
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
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&family=Barlow:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

  /* ── RESET ── */
  .stApp { background-color: #080808; font-family: 'Barlow', sans-serif; color: #c8c8c8; }
  header[data-testid="stHeader"] { background: transparent !important; }
  #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
  section[data-testid="stSidebar"] { display: none !important; }

  /* ── HEADER ── */
  .korcz-header {
    display: flex; align-items: center; gap: 20px;
    padding: 22px 0 18px; margin-bottom: 32px;
    border-bottom: 2px solid #1e1e1e;
    position: relative;
  }
  .korcz-header::after {
    content: ''; position: absolute;
    bottom: -2px; left: 0; width: 120px; height: 2px;
    background: #e5001a;
  }
  .kh-brand { font-family:'Barlow Condensed',sans-serif; }
  .kh-brand .name { font-size: 2.4rem; font-weight: 900; color: #e5001a; letter-spacing: 3px; line-height: 1; }
  .kh-brand .tagline { font-size: .72rem; font-weight: 600; color: #3a3a3a; letter-spacing: 4px; text-transform: uppercase; margin-top: 3px; }
  .kh-right { margin-left: auto; text-align: right; }
  .kh-ver { font-size: .65rem; color: #2a2a2a; letter-spacing: 3px; text-transform: uppercase; font-family:'Barlow Condensed',sans-serif; }
  .kh-live { display: flex; align-items: center; gap: 6px; justify-content: flex-end; margin-top: 5px; }
  .kh-dot { width: 7px; height: 7px; background: #00c84a; border-radius: 50%; box-shadow: 0 0 8px #00c84a55; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }
  .kh-live-txt { font-size: .68rem; color: #00c84a; letter-spacing: 2px; font-family:'Barlow Condensed',sans-serif; text-transform: uppercase; }

  /* ── KARTY ── */
  .card {
    background: #0e0e0e; border: 1px solid #1c1c1c; border-radius: 6px;
    padding: 20px 24px; margin-bottom: 16px;
  }
  .card-title {
    font-family: 'Barlow Condensed', sans-serif; font-size: .75rem; font-weight: 700;
    color: #e5001a; letter-spacing: 4px; text-transform: uppercase;
    margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #1c1c1c;
    display: flex; align-items: center; gap: 8px;
  }

  /* ── TRYB BAR ── */
  .tryb-desc {
    font-size: .82rem; color: #555; margin: 10px 0 18px;
    padding: 10px 14px; background: #0a0a0a; border-left: 3px solid #1e1e1e; border-radius: 0 4px 4px 0;
  }

  /* ── UPLOADER ── */
  [data-testid="stFileUploader"] {
    background: #090909 !important; border: 1px dashed #222 !important;
    border-radius: 6px !important; padding: 28px !important;
    transition: all .25s;
  }
  [data-testid="stFileUploader"]:hover { border-color: #e5001a !important; background: #100004 !important; }
  [data-testid="stFileUploaderDropzone"] p { color: #444 !important; font-size: .85rem !important; }
  [data-testid="stFileUploaderDropzoneInstructions"] { color: #333 !important; }

  /* ── METRYKI ── */
  [data-testid="stMetric"] {
    background: #0b0b0b !important; border: 1px solid #1a1a1a !important;
    border-radius: 6px !important; padding: 16px 20px !important;
    position: relative; overflow: hidden;
  }
  [data-testid="stMetric"]::before {
    content:''; position:absolute; top:0; left:0;
    width:3px; height:100%; background:#e5001a;
  }
  [data-testid="stMetricLabel"] { color:#3a3a3a !important; font-size:.64rem !important; letter-spacing:2.5px !important; text-transform:uppercase !important; font-family:'Barlow Condensed',sans-serif !important; }
  [data-testid="stMetricValue"] { color:#fff !important; font-family:'Barlow Condensed',sans-serif !important; font-size:2.1rem !important; font-weight:900 !important; line-height:1.1 !important; }

  /* ── TABELA ── */
  .tbl-head { font-family:'Barlow Condensed',sans-serif; font-size:.62rem; color:#2e2e2e; letter-spacing:2.5px; text-transform:uppercase; }
  .tbl-num { font-size:.8rem; color:#2a2a2a; padding-top:8px; }
  .tbl-file { font-size:.76rem; color:#555; word-break:break-all; line-height:1.4; padding-top:5px; }
  .strip-p3  { border-left:3px solid #3366cc; padding-left:8px; }
  .strip-ddu { border-left:3px solid #cc0015; padding-left:8px; }
  .wagon-val { font-family:'JetBrains Mono',monospace; font-size:.95rem; color:#f0f0f0; font-weight:600; padding-top:6px; letter-spacing:.5px; }
  .meta-val  { font-size:.78rem; color:#666; padding-top:7px; }
  .meta-hi   { font-size:.78rem; color:#888; padding-top:7px; }

  /* ── BADGES ── */
  .badge {
    display:inline-flex; align-items:center; gap:5px;
    padding:3px 9px; border-radius:3px;
    font-family:'Barlow Condensed',sans-serif; font-size:.68rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
  }
  .badge::before { content:''; width:5px; height:5px; border-radius:50%; display:inline-block; }
  .b-ok    { background:#011a0a; color:#00c84a; border:1px solid #003d14; }
  .b-ok::before { background:#00c84a; box-shadow:0 0 4px #00c84a; }
  .b-warn  { background:#160d00; color:#e08800; border:1px solid #4d3000; }
  .b-warn::before { background:#e08800; }
  .b-err   { background:#160003; color:#ff3350; border:1px solid #4d000f; }
  .b-err::before  { background:#ff3350; }
  .b-sent  { background:#00102e; color:#3d88ff; border:1px solid #003080; }
  .b-sent::before { background:#3d88ff; }
  .b-p3    { background:#000d26; color:#5599ff; border:1px solid #002266; }
  .b-p3::before   { background:#5599ff; }
  .b-ddu   { background:#160003; color:#ff6070; border:1px solid #4d0010; }
  .b-ddu::before  { background:#ff6070; }

  /* ── INPUTS ── */
  .stTextInput>label, .stSelectbox>label {
    color:#3a3a3a !important; font-size:.65rem !important;
    letter-spacing:2px !important; text-transform:uppercase !important;
    font-family:'Barlow Condensed',sans-serif !important;
  }
  .stTextInput>div>div>input {
    background:#080808 !important; border:1px solid #222 !important;
    color:#ddd !important; border-radius:4px !important; font-size:.9rem !important;
    padding:9px 12px !important; font-family:'Barlow',sans-serif !important;
  }
  .stTextInput>div>div>input:focus { border-color:#e5001a !important; box-shadow:0 0 0 2px rgba(229,0,26,.12) !important; }
  .stSelectbox>div>div { background:#080808 !important; border:1px solid #222 !important; color:#ddd !important; border-radius:4px !important; }

  /* ── BUTTONY ── */
  .stButton>button {
    background:#e5001a !important; color:#fff !important; border:none !important;
    border-radius:4px !important; font-family:'Barlow Condensed',sans-serif !important;
    font-size:.9rem !important; font-weight:700 !important; letter-spacing:2px !important;
    text-transform:uppercase !important; padding:10px 22px !important;
    transition:all .15s !important;
  }
  .stButton>button:hover { background:#c00016 !important; transform:translateY(-1px) !important; }
  .stButton>button:active { transform:translateY(0) !important; }
  .btn-ghost>button { background:transparent !important; border:1px solid #222 !important; color:#444 !important; }
  .btn-ghost>button:hover { border-color:#555 !important; color:#aaa !important; background:transparent !important; transform:none !important; }
  .btn-sm>button { padding:6px 14px !important; font-size:.8rem !important; }

  /* ── PROGRESS ── */
  .stProgress>div>div>div { background:linear-gradient(90deg,#e5001a,#ff3344) !important; border-radius:2px !important; }

  /* ── EXPANDER ── */
  .streamlit-expanderHeader { background:#090909 !important; color:#333 !important; font-size:.75rem !important; border-radius:4px !important; border:1px solid #181818 !important; }
  .streamlit-expanderContent { background:#060606 !important; }

  /* ── CODE ── */
  pre, code { font-family:'JetBrains Mono',monospace !important; font-size:.78rem !important; background:#060606 !important; color:#888 !important; }

  /* ── ALERT ── */
  .stAlert { border-radius:4px !important; }

  /* ── HR ── */
  hr { border:none !important; border-top:1px solid #141414 !important; margin:6px 0 !important; }

  /* ── LOADING BOX ── */
  .load-box {
    background:#0a0a0a; border:1px solid #1e1e1e; border-radius:6px;
    padding:18px 22px; display:flex; align-items:center; gap:14px;
    font-size:.84rem; color:#555;
  }
  .load-spinner {
    width:18px; height:18px; border:2px solid #222; border-top-color:#e5001a;
    border-radius:50%; animation:spin .8s linear infinite; flex-shrink:0;
  }
  @keyframes spin { to { transform:rotate(360deg); } }

  /* ── PANEL EDYCJI ── */
  .edit-header {
    display:flex; align-items:center; gap:12px; margin-bottom:20px;
    padding-bottom:12px; border-bottom:1px solid #1c1c1c;
  }
  .edit-header .eh-num {
    background:#e5001a; color:#fff; width:28px; height:28px;
    border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-family:'Barlow Condensed',sans-serif; font-weight:900; font-size:.9rem;
  }
  .edit-header .eh-title { font-family:'Barlow Condensed',sans-serif; font-size:1.05rem; color:#ccc; letter-spacing:1px; }
  .edit-header .eh-file  { font-size:.75rem; color:#3a3a3a; margin-left:auto; }

  /* ── STOPKA ── */
  .korcz-footer {
    margin-top:56px; padding-top:20px; border-top:1px solid #141414;
    text-align:center; font-family:'Barlow Condensed',sans-serif;
    font-size:.62rem; letter-spacing:3px; text-transform:uppercase; color:#222;
  }
  .korcz-footer em { color:#2e2e2e; font-style:normal; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# LOGO + HEADER
# ---------------------------------------------------------------------------
LOGO_PATH = Path(__file__).parent / "logo_spkkorcz.png"

def _logo_html() -> str:
    try:
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" style="height:58px;filter:brightness(1.05);">'
    except Exception:
        return '<div style="font-size:2.2rem;line-height:1">🚂</div>'

st.markdown(f"""
<div class="korcz-header">
  {_logo_html()}
  <div class="kh-brand">
    <div class="name">KORCZ</div>
    <div class="tagline">System Skanowania Dokumentów Kolejowych</div>
  </div>
  <div class="kh-right">
    <div class="kh-ver">v5.0 &nbsp;·&nbsp; DDU / P3 / Mw 581</div>
    <div class="kh-live">
      <div class="kh-dot"></div>
      <span class="kh-live-txt">System aktywny</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------------------
ARKUSZ_P3_URL  = st.secrets.get("ARKUSZ_P3_URL",  "")
ARKUSZ_DDU_URL = st.secrets.get("ARKUSZ_DDU_URL", "")

@st.cache_resource
def get_google_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# ---------------------------------------------------------------------------
# EASYOCR — SINGLETON (ładowany raz, cache w session_state)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_ocr_reader():
    """Ładuje model EasyOCR raz — pierwsze uruchomienie może zająć ~30s."""
    return easyocr.Reader(["pl", "en"], gpu=False, verbose=False)

# ---------------------------------------------------------------------------
# OBSŁUGA PLIKÓW
# ---------------------------------------------------------------------------
SUPPORTED_EXT = ["pdf", "jpg", "jpeg", "png"]

def _img_to_np(img: Image.Image) -> np.ndarray:
    """PIL → numpy RGB, skaluje do min. 1800px szerokości."""
    img_rgb = img.convert("RGB")
    w, h = img_rgb.size
    if w < 1800:
        scale = 1800 / w
        img_rgb = img_rgb.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return np.array(img_rgb)

def ocr_z_obrazu(img: Image.Image) -> str:
    """
    OCR przez EasyOCR.
    Zwraca tekst posortowany góra→dół, lewo→prawo.
    """
    reader = get_ocr_reader()
    img_np = _img_to_np(img)

    # paragraph=False — lepiej dla tabelek z pojedynczymi cyframi
    results = reader.readtext(
        img_np,
        detail=1,
        paragraph=False,
        width_ths=0.7,
        height_ths=0.7,
    )

    if not results:
        return ""

    # Sortuj po Y (wiersz), potem X (kolumna)
    results_sorted = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))

    # Buduj linie z progiem pewności
    lines = []
    for bbox, text, conf in results_sorted:
        if conf > 0.15 and text.strip():
            lines.append(text.strip())

    return "\n".join(lines)

def _podglad_bytes(img: Image.Image, max_w: int = 1200) -> bytes:
    """Zmniejsza obraz do podglądu, zwraca PNG bytes."""
    img_c = img.copy().convert("RGB")
    if img_c.width > max_w:
        r = max_w / img_c.width
        img_c = img_c.resize((max_w, int(img_c.height * r)), Image.LANCZOS)
    buf = io.BytesIO()
    img_c.save(buf, format="PNG")
    return buf.getvalue()

def przetworz_plik(file_bytes: bytes, filename: str, tryb: str = "AUTO") -> list:
    """
    Przetwarza jeden plik (PDF / JPG / PNG).
    Zwraca listę rekordów-słowników.
    """
    ext = Path(filename).suffix.lower().lstrip(".")

    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        n_stron = len(doc)
        ddu_idx = _znajdz_strone_ddu(doc)

        # Podgląd (150 DPI)
        pix_prev = doc[ddu_idx].get_pixmap(dpi=150)
        img_prev = Image.open(io.BytesIO(pix_prev.tobytes()))
        podglad  = _podglad_bytes(img_prev)

        # OCR (280 DPI — balans jakość/szybkość)
        pix_ocr = doc[ddu_idx].get_pixmap(dpi=280)
        img_ocr = Image.open(io.BytesIO(pix_ocr.tobytes()))
        tekst   = ocr_z_obrazu(img_ocr)
        doc.close()
        meta = dict(ddu_strona=ddu_idx + 1, n_stron=n_stron)

    else:  # JPG / PNG
        img_raw = Image.open(io.BytesIO(file_bytes))
        podglad = _podglad_bytes(img_raw)
        tekst   = ocr_z_obrazu(img_raw)
        meta    = dict(ddu_strona=1, n_stron=1)

    typ = tryb if tryb != "AUTO" else wykryj_typ(tekst)
    dat = data_z_ocr(tekst)
    lok = lokalizacja_z_ocr(tekst)

    base = dict(
        filename=filename, typ=typ,
        data=dat, lokalizacja=lok,
        podglad_png=podglad, ocr_tekst=tekst,
        wyslano=False, blad="",
        **meta,
    )

    rekordy = []
    if typ == "P3":
        w = _wagon_z_nazwy(filename) or wagon_jeden(tekst)
        rekordy.append({**base, "wagon": w, "nr_dop": nr_dop_z_ocr(tekst)})
    else:
        wagony = wagony_wszystkie(tekst) or (
            [_wagon_z_nazwy(filename)] if _wagon_z_nazwy(filename) else []
        )
        if wagony:
            for w in wagony:
                rekordy.append({**base, "wagon": w, "nr_dop": ""})
        else:
            rekordy.append({
                **base, "wagon": "", "nr_dop": "",
                "blad": "Nie znaleziono numerów wagonów",
            })

    return rekordy

def _znajdz_strone_ddu(doc) -> int:
    """Heurystyka: szuka strony z DDU od końca dokumentu."""
    if len(doc) == 1:
        return 0
    reader = get_ocr_reader()
    for i in range(len(doc) - 1, max(len(doc) - 9, -1), -1):
        pix = doc[i].get_pixmap(dpi=90)
        img = Image.open(io.BytesIO(pix.tobytes()))
        img_np = _img_to_np(img)
        wyniki = reader.readtext(img_np, detail=0, paragraph=True)
        tekst_q = " ".join(wyniki).upper()
        if "DOPUSZCZENIE" in tekst_q or ("PROTOKÓŁ" in tekst_q and "P6" in tekst_q) or "MW 581" in tekst_q:
            return i
    return len(doc) - 1

# ===========================================================================
# ROZPOZNAWANIE TYPU
# ===========================================================================
_SLOWA_P3 = [
    "PROTOKÓŁ P6", "PROTOKOL P6",
    "DOPUSZCZENIE DO UŻYTKOWANIA WAGONU TOWAROWEGO",
    "PRZEGLĄD P3", "PRZEGLAD P3",
]
_SLOWA_DDU = [
    "MW 581", "Mw 581", "ZAWIADOMIENIE O NAPRAWIE",
    "PO NAPRAWIE POZIOMU P1", "P1/P2",
    "NAPRAWIE WAGONÓW", "NAPRAWIE WAGONOW",
    "PROTOKÓŁ NR", "PROTOKOL NR",
    "ODBIORU WAGONÓW TOWAROWYCH", "ODBIORU WAGONOW TOWAROWYCH",
    "ZAWIADOMIENIE MW",
]

def wykryj_typ(text: str) -> str:
    up = text.upper()
    for kw in _SLOWA_P3:
        if kw.upper() in up:
            return "P3"
    for kw in _SLOWA_DDU:
        if kw.upper() in up:
            return "DDU"
    if len(_wagony_raw(text)) > 1:
        return "DDU"
    return "P3"

# ===========================================================================
# EKSTRAKCJA DANYCH
# ===========================================================================
_PREFIKSY_TEL = ("48881","48882","48535","48538","48500","48501","48502",
                 "48503","48504","48505","48506","48507","48508","48509",
                 "881","882","535","538")

def _czy_telefon(raw: str) -> bool:
    return any(raw.startswith(p) for p in _PREFIKSY_TEL)

def formatuj_wagon(cyfry: str) -> str:
    d = re.sub(r"\D", "", cyfry)[:12]
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}" if len(d) == 12 else cyfry

def _wagony_raw(text: str) -> list:
    """
    Wyciąga 12-cyfrowe numery wagonów z tekstu (deduplikowane).
    Obsługuje format z EasyOCR: '3 3 5 1 5 3 3 2 1 3 7 7' (spacje między cyframi).
    """
    text_c = re.sub(r"(?m)^\s*\d{1,2}[\.\)\s]\s*", " ", text)
    found, seen = [], set()

    # Wzorzec 1 — cyfry po jednej (EasyOCR z tabelek)
    for m in re.finditer(r"(?<!\d)(\d\s){11}\d(?!\d)", text_c):
        raw = re.sub(r"\D", "", m.group(0))
        if len(raw) == 12 and raw not in seen and not _czy_telefon(raw):
            seen.add(raw); found.append(raw)

    # Wzorzec 2 — cyfry przyklejone / z myślnikami
    for m in re.finditer(r"\b(\d[\d\s\-\.]{9,16}\d)\b", text_c):
        raw = re.sub(r"\D", "", m.group(1))
        if len(raw) == 12 and raw not in seen and not _czy_telefon(raw):
            seen.add(raw); found.append(raw)

    return found

def _wagon_z_nazwy(fname: str) -> str:
    m = re.search(r"(\d{4})[\s_\-]?(\d{4})[\s_\-]?(\d{3})[\s_\-](\d)", fname)
    if m:
        d = "".join(m.groups())
        return formatuj_wagon(d) if len(d) == 12 else ""
    return ""

def wagon_jeden(text: str) -> str:
    r = _wagony_raw(text)
    return formatuj_wagon(r[0]) if r else ""

def wagony_wszystkie(text: str) -> list:
    return [formatuj_wagon(r) for r in _wagony_raw(text)]

def nr_dop_z_ocr(text: str) -> str:
    m = re.search(r"\bNr[\.\s:]{1,5}([\d\s]{5,14})", text, re.IGNORECASE)
    if m:
        v = re.sub(r"\s", "", m.group(1))
        if 6 <= len(v) <= 12:
            return v
    return ""

def data_z_ocr(text: str) -> str:
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

_ZNANE_LOK = [
    "KWK Janina","KWK Ziemowit","KWK Piast","KWK Murcki","KWK Pniówek",
    "KWK Budryk","KWK Bielszowice","KWK Mysłowice","KWK Bolesław Śmiały",
    "Dwory Terminal","Terminal Dwory",
    "Elektrownia Jaworzno","Elektrownia Łagisza","Elektrownia Siersza",
    "Elektrownia Rybnik","Elektrownia Połaniec",
]

def lokalizacja_z_ocr(text: str) -> str:
    up = text.upper()
    for lok in _ZNANE_LOK:
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
# SESSION STATE
# ===========================================================================
if "wyniki"        not in st.session_state: st.session_state.wyniki = []
if "edytowany_idx" not in st.session_state: st.session_state.edytowany_idx = None
if "tryb"          not in st.session_state: st.session_state.tryb = "AUTO"

# ===========================================================================
# MODEL OCR — preload w tle z komunikatem
# ===========================================================================
if "ocr_gotowy" not in st.session_state:
    with st.container():
        st.markdown(
            '<div class="load-box"><div class="load-spinner"></div>'
            '<span>Ładowanie modelu EasyOCR — jednorazowo, zajmuje chwilę…</span></div>',
            unsafe_allow_html=True,
        )
    get_ocr_reader()          # preload
    st.session_state.ocr_gotowy = True
    st.rerun()

# ===========================================================================
# SEKCJA 1 — TRYB + UPLOAD
# ===========================================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📂 Wgraj dokumenty</div>', unsafe_allow_html=True)

# Przyciski trybu
c1, c2, c3, _ = st.columns([1.1, 0.85, 1.9, 4.1])
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

_TRYB_KOLOR = {"AUTO": "#3a3a3a", "P3": "#3366cc", "DDU": "#cc0015"}
_TRYB_OPIS  = {
    "AUTO": "Automatyczne wykrywanie — program rozpozna typ dokumentu na podstawie treści.",
    "P3":   "Przegląd P3 — jeden wagon na plik, zapis do arkusza P3.",
    "DDU":  "DDU / Mw 581 / P1·P2 — wyciąga wszystkie wagony z tabeli, zapis do arkusza DDU.",
}
st.markdown(
    f'<div class="tryb-desc" style="border-left-color:{_TRYB_KOLOR[st.session_state.tryb]}">'
    f'<strong style="color:{_TRYB_KOLOR[st.session_state.tryb]}">{st.session_state.tryb}</strong>'
    f' &nbsp;— {_TRYB_OPIS[st.session_state.tryb]}</div>',
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Przeciągnij pliki lub kliknij — PDF, JPG, JPEG, PNG",
    type=SUPPORTED_EXT,
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

# ── Przetwarzanie ──────────────────────────────────────────────────────────
if uploaded_files:
    przetworzone = {w["filename"] for w in st.session_state.wyniki}
    nowe = [f for f in uploaded_files if f.name not in przetworzone]

    if nowe:
        prog = st.progress(0, text="Inicjalizacja…")
        ph   = st.empty()

        for i, plik in enumerate(nowe):
            prog.progress(i / len(nowe), text=f"⚙️ OCR: {plik.name}  ({i+1}/{len(nowe)})")
            ph.markdown(
                f'<div class="load-box"><div class="load-spinner"></div>'
                f'<span>Przetwarzam <strong style="color:#aaa">{plik.name}</strong>…</span></div>',
                unsafe_allow_html=True,
            )
            try:
                rekordy = przetworz_plik(plik.read(), plik.name, st.session_state.tryb)
                st.session_state.wyniki.extend(rekordy)
            except Exception as e:
                st.session_state.wyniki.append(dict(
                    filename=plik.name, typ="?",
                    wagon="", nr_dop="", data="", lokalizacja="",
                    ddu_strona=0, n_stron=0,
                    podglad_png=None, ocr_tekst="",
                    wyslano=False, blad=str(e),
                ))
            time.sleep(0.02)

        prog.progress(1.0, text="✅ Gotowe!")
        ph.empty()
        time.sleep(0.5)
        prog.empty()
        st.rerun()

# ===========================================================================
# SEKCJA 2 — DASHBOARD + TABELA
# ===========================================================================
wyniki = st.session_state.wyniki

if wyniki:
    # Metryki
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

    # Tabela wyników
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📋 Wyniki skanowania</div>', unsafe_allow_html=True)

    hc = st.columns([0.28, 1.8, 0.6, 1.55, 0.95, 1.55, 0.95, 0.85, 0.5])
    for col, h in zip(hc, ["#","Plik","Typ","Nr wagonu","Nr dop.","Lokalizacja","Data","Status",""]):
        col.markdown(f'<div class="tbl-head">{h}</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    for idx, w in enumerate(wyniki):
        rc = st.columns([0.28, 1.8, 0.6, 1.55, 0.95, 1.55, 0.95, 0.85, 0.5])

        rc[0].markdown(f'<div class="tbl-num">{idx+1}</div>', unsafe_allow_html=True)

        bar = "strip-p3" if w["typ"] == "P3" else "strip-ddu"
        rc[1].markdown(f'<div class="{bar} tbl-file">{w["filename"]}</div>', unsafe_allow_html=True)

        tb = '<span class="badge b-p3">P3</span>' if w["typ"] == "P3" else '<span class="badge b-ddu">DDU</span>'
        rc[2].markdown(f'<div style="padding-top:5px">{tb}</div>', unsafe_allow_html=True)

        rc[3].markdown(f'<div class="wagon-val">{w["wagon"] or "—"}</div>', unsafe_allow_html=True)
        rc[4].markdown(f'<div class="meta-val">{w["nr_dop"] or "—"}</div>', unsafe_allow_html=True)
        rc[5].markdown(f'<div class="meta-hi">{w["lokalizacja"] or "—"}</div>', unsafe_allow_html=True)
        rc[6].markdown(f'<div class="meta-val">{w["data"] or "—"}</div>', unsafe_allow_html=True)

        if w["blad"]:        sb = '<span class="badge b-err">Błąd</span>'
        elif w["wyslano"]:   sb = '<span class="badge b-sent">Wysłano</span>'
        elif w["wagon"]:     sb = '<span class="badge b-ok">OK</span>'
        else:                sb = '<span class="badge b-warn">Korekta</span>'
        rc[7].markdown(f'<div style="padding-top:5px">{sb}</div>', unsafe_allow_html=True)

        with rc[8]:
            if st.button("✏️", key=f"e{idx}", help="Edytuj / wyślij"):
                st.session_state.edytowany_idx = idx

        st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── BATCH WYŚLIJ ───────────────────────────────────────────────────────
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

            if st.button(f"🚀  WYŚLIJ DO GOOGLE SHEETS  ·  {lbl}",
                         type="primary", use_container_width=True):
                try:
                    client = get_google_client()
                    n_ok_p3 = n_ok_ddu = 0

                    if gp3 and ARKUSZ_P3_URL:
                        sh   = client.open_by_url(ARKUSZ_P3_URL).sheet1
                        lp_n = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                        rows = []
                        for off, (i, w) in enumerate(gp3):
                            rows.append([lp_n + off, w["nr_dop"], w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sh.append_rows(rows)
                        n_ok_p3 = len(rows)

                    if gddu and ARKUSZ_DDU_URL:
                        sh   = client.open_by_url(ARKUSZ_DDU_URL).sheet1
                        lp_n = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                        rows = []
                        for off, (i, w) in enumerate(gddu):
                            rows.append([lp_n + off, w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sh.append_rows(rows)
                        n_ok_ddu = len(rows)

                    st.success(f"✅ Zapisano {n_ok_p3} × P3  i  {n_ok_ddu} × DDU do Google Sheets.")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Błąd połączenia z Google Sheets: {e}")

        with cc:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("🗑 Wyczyść", use_container_width=True):
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
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="edit-header">'
            f'<div class="eh-num">{idx + 1}</div>'
            f'<div class="eh-title">Edycja rekordu</div>'
            f'<div class="eh-file">{w["filename"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_img, col_form = st.columns([5, 4], gap="large")

        with col_img:
            st.markdown('<div style="font-size:.62rem;color:#2a2a2a;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:8px">Podgląd dokumentu</div>', unsafe_allow_html=True)
            if w["podglad_png"]:
                st.image(w["podglad_png"], use_container_width=True)
                st.caption(f'Strona {w.get("ddu_strona","?")} / {w.get("n_stron","?")}')
            else:
                st.warning("Brak podglądu — błąd przetwarzania.")
            with st.expander("🔍 Surowy tekst OCR (diagnostyka)"):
                st.code(w.get("ocr_tekst", "(brak)"), language=None)

        with col_form:
            st.markdown('<div style="font-size:.62rem;color:#2a2a2a;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:16px">Dane do rejestru</div>', unsafe_allow_html=True)

            new_typ  = st.selectbox("Typ dokumentu", ["P3","DDU"],
                                    index=0 if w["typ"] == "P3" else 1,
                                    key=f"sel_{idx}")
            wagon_v  = st.text_input("Numer wagonu  ✱", value=w["wagon"],
                                     placeholder="3351 5332 137-7", key=f"wg_{idx}")
            nrdop_v  = ""
            if new_typ == "P3":
                nrdop_v = st.text_input("Numer dopuszczenia", value=w["nr_dop"],
                                        placeholder="17044086", key=f"nd_{idx}")
            data_v   = st.text_input("Data wystawienia", value=w["data"],
                                     placeholder="DD.MM.RRRR", key=f"dt_{idx}")
            lok_v    = st.text_input("Miejscowość / Zakład", value=w["lokalizacja"],
                                     placeholder="KWK Janina", key=f"lk_{idx}")

            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([2, 2, 1])

            with b1:
                if st.button("💾 Zapisz zmiany", key=f"sv_{idx}", use_container_width=True):
                    st.session_state.wyniki[idx].update(
                        typ=new_typ, wagon=wagon_v, nr_dop=nrdop_v,
                        data=data_v, lokalizacja=lok_v, blad="",
                    )
                    st.success("Zmiany zapisane.")

            with b2:
                if st.button("✅ Wyślij ten wpis", key=f"sn_{idx}",
                             use_container_width=True, type="primary"):
                    if not wagon_v.strip():
                        st.error("❌ Numer wagonu jest wymagany.")
                    else:
                        try:
                            client = get_google_client()
                            url = ARKUSZ_P3_URL if new_typ == "P3" else ARKUSZ_DDU_URL
                            sh   = client.open_by_url(url).sheet1
                            lp_n = 1 if len(sh.col_values(1)) <= 1 else int(sh.col_values(1)[-1]) + 1
                            row  = ([lp_n, nrdop_v, lok_v, data_v, wagon_v.strip()]
                                    if new_typ == "P3"
                                    else [lp_n, lok_v, data_v, wagon_v.strip()])
                            sh.append_rows([row])
                            st.session_state.wyniki[idx].update(
                                typ=new_typ, wagon=wagon_v, nr_dop=nrdop_v,
                                data=data_v, lokalizacja=lok_v, wyslano=True, blad="",
                            )
                            st.success(f"✅ LP={lp_n} → arkusz {new_typ}")
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
  KORCZ Serwis Pojazdów Kolejowych &nbsp;·&nbsp; v5.0 &nbsp;·&nbsp; EasyOCR Engine
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <em>P3 → Arkusz Przeglądów</em>
  &nbsp;·&nbsp;
  <em>DDU / Mw 581 / P1·P2 → Arkusz DDU</em>
</div>
""", unsafe_allow_html=True)
