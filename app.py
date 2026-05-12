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
# STYL CSS — industrialny, czarno-czerwony, KORCZ brand
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Barlow:wght@400;500;600&display=swap');

  .stApp { background-color: #0d0d0d; font-family: 'Barlow', sans-serif; }
  header[data-testid="stHeader"] { background: transparent; }
  #MainMenu, footer { visibility: hidden; }

  .korcz-header {
    display: flex; align-items: center; gap: 24px;
    padding: 20px 0 16px 0; border-bottom: 3px solid #e5001a; margin-bottom: 32px;
  }
  .korcz-logo-text { font-family: 'Barlow Condensed', sans-serif; }
  .korcz-logo-text .brand { font-size: 2.6rem; font-weight: 900; color: #e5001a; letter-spacing: 2px; line-height: 1; }
  .korcz-logo-text .sub   { font-size: 1rem; font-weight: 600; color: #cccccc; letter-spacing: 3px; text-transform: uppercase; }

  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px; padding: 20px 24px; margin-bottom: 16px; }
  .card-header { font-family: 'Barlow Condensed', sans-serif; font-size: 1.1rem; font-weight: 700; color: #e5001a; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #2a2a2a; }

  .badge { display: inline-block; padding: 2px 10px; border-radius: 2px; font-size: 0.75rem; font-weight: 700; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 1px; text-transform: uppercase; }
  .badge-ok      { background: #003d1a; color: #00d455; border: 1px solid #00d455; }
  .badge-warn    { background: #3d2200; color: #ffa500; border: 1px solid #ffa500; }
  .badge-error   { background: #3d0008; color: #ff4060; border: 1px solid #ff4060; }
  .badge-sent    { background: #002040; color: #4090ff; border: 1px solid #4090ff; }
  .badge-p3      { background: #001840; color: #5599ff; border: 1px solid #5599ff; }
  .badge-ddu     { background: #3d0008; color: #ff8090; border: 1px solid #ff5060; }

  .section-label { font-family: 'Barlow Condensed', sans-serif; font-size: 0.7rem; letter-spacing: 3px; text-transform: uppercase; color: #666; margin-bottom: 4px; }
  .wagon-num { font-family: 'Barlow Condensed', sans-serif; font-size: 1.05rem; color: #fff; font-weight: 700; }
  .filename-cell { color: #888; font-size: 0.8rem; word-break: break-all; }

  .stTextInput > label { color: #aaa !important; font-size: 0.8rem !important; letter-spacing: 1px; text-transform: uppercase; }
  .stTextInput > div > div > input { background: #111 !important; border: 1px solid #333 !important; color: #fff !important; border-radius: 2px !important; }
  .stTextInput > div > div > input:focus { border-color: #e5001a !important; box-shadow: 0 0 0 1px #e5001a !important; }

  .stButton > button { background: #e5001a !important; color: #fff !important; border: none !important; border-radius: 2px !important; font-family: 'Barlow Condensed', sans-serif !important; font-size: 1rem !important; font-weight: 700 !important; letter-spacing: 2px !important; text-transform: uppercase !important; padding: 10px 24px !important; }
  .stButton > button:hover { background: #b30015 !important; }
  .btn-secondary > button { background: #1a1a1a !important; border: 1px solid #444 !important; color: #ccc !important; }
  .btn-secondary > button:hover { border-color: #e5001a !important; color: #fff !important; }

  [data-testid="stFileUploader"] { background: #111 !important; border: 2px dashed #333 !important; border-radius: 4px !important; padding: 24px !important; }
  [data-testid="stFileUploader"]:hover { border-color: #e5001a !important; }
  .stProgress > div > div > div { background: #e5001a !important; }
  hr { border-color: #2a2a2a !important; }
  .streamlit-expanderHeader { background: #111 !important; color: #888 !important; font-size: 0.8rem !important; border-radius: 2px !important; }

  [data-testid="stMetric"] { background: #111; border: 1px solid #2a2a2a; border-radius: 4px; padding: 16px; }
  [data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.75rem !important; letter-spacing: 1px; text-transform: uppercase; }
  [data-testid="stMetricValue"] { color: #fff !important; font-family: 'Barlow Condensed', sans-serif !important; font-size: 2rem !important; }

  .stTabs [data-baseweb="tab-list"] { background: #0d0d0d; border-bottom: 2px solid #2a2a2a; }
  .stTabs [data-baseweb="tab"] { color: #666; font-family: 'Barlow Condensed', sans-serif; font-size: 1rem; letter-spacing: 1px; text-transform: uppercase; }
  .stTabs [aria-selected="true"] { color: #e5001a !important; border-bottom: 2px solid #e5001a !important; }

  .type-strip-p3  { border-left: 4px solid #5599ff; padding-left: 8px; }
  .type-strip-ddu { border-left: 4px solid #e5001a; padding-left: 8px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# LOGO
# ---------------------------------------------------------------------------
LOGO_PATH = Path(__file__).parent / "logo_spkkorcz.png"

def get_logo_html() -> str:
    try:
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" style="height:64px;">'
    except Exception:
        return '<div style="font-size:2rem;">🚂</div>'

st.markdown(f"""
<div class="korcz-header">
  {get_logo_html()}
  <div class="korcz-logo-text">
    <div class="brand">KORCZ</div>
    <div class="sub">Skaner DDU / Przegląd P3 &nbsp;·&nbsp; v3.0</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# GOOGLE SHEETS — dwa oddzielne arkusze
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
# ROZPOZNANIE TYPU DOKUMENTU
# ===========================================================================

SLOWA_P3 = [
    "PROTOKÓŁ", "P6", "DOPUSZCZENIE DO UŻYTKOWANIA WAGONU TOWAROWEGO",
    "PRZEGLĄD P3", "PRZEGLAD P3", "PROTOKOL",
]
SLOWA_DDU = [
    "MW 581", "Mw 581", "ZAWIADOMIENIE O NAPRAWIE",
    "PO NAPRAWIE POZIOMU P1", "P1/P2", "NAPRAWIE WAGONÓW", "NAPRAWIE WAGONOW",
    "ZAWIADOMIENIE MW", "PROTOKÓŁ NR", "PROTOKOL NR",
    "ODBIORU WAGONÓW TOWAROWYCH", "ODBIORU WAGONOW TOWAROWYCH",
]

def wykryj_typ(text: str) -> str:
    """Zwraca 'P3' lub 'DDU'."""
    upper = text.upper()
    # Najpierw P3 (bardziej specyficzne słowa)
    for kw in SLOWA_P3:
        if kw.upper() in upper:
            return "P3"
    for kw in SLOWA_DDU:
        if kw.upper() in upper:
            return "DDU"
    # Heurystyka: wiele wagonów w tabeli → DDU
    if len(_znajdz_wszystkie_wagony_raw(text)) > 1:
        return "DDU"
    return "P3"


# ===========================================================================
# EKSTRAKCJA DANYCH
# ===========================================================================

def formatuj_wagon(cyfry_12: str) -> str:
    d = re.sub(r"\D", "", cyfry_12)[:12]
    if len(d) < 12:
        return cyfry_12
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}"

def _znajdz_wszystkie_wagony_raw(text: str) -> list:
    """
    Wyciąga wszystkie 12-cyfrowe numery wagonów.
    Ignoruje numery porządkowe (1., 2. ...) i daty.
    """
    # Usuń numery LP na początku linii
    text_clean = re.sub(r"(?m)^\s*\d{1,2}[\.\)\s]\s*", " ", text)

    found = []
    for m in re.finditer(r"\b(\d[\d\s\-\.]{9,16}\d)\b", text_clean):
        raw = re.sub(r"\D", "", m.group(1))
        if len(raw) == 12:
            # Odrzuć numery telefonów
            if raw.startswith("48") or raw.startswith("881") or raw.startswith("882"):
                continue
            found.append(raw)

    # Deduplikacja z zachowaniem kolejności
    seen = set()
    result = []
    for r in found:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result

def wagon_z_nazwy_pliku(filename: str) -> str:
    m = re.search(r"(\d{4})[\s_\-]?(\d{4})[\s_\-]?(\d{3})[\s_\-](\d)", filename)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)
    return ""

def wagon_z_ocr(text: str) -> str:
    wyniki = _znajdz_wszystkie_wagony_raw(text)
    return formatuj_wagon(wyniki[0]) if wyniki else ""

def wszystkie_wagony_z_ocr(text: str) -> list:
    return [formatuj_wagon(r) for r in _znajdz_wszystkie_wagony_raw(text)]

def nr_dop_z_ocr(text: str) -> str:
    m = re.search(r"\bNr[\.\s:]{1,5}([\d\s]{5,14})", text, re.IGNORECASE)
    if m:
        val = re.sub(r"\s", "", m.group(1)).strip()
        if 6 <= len(val) <= 12:
            return val
    return ""

def data_z_ocr(text: str) -> str:
    NAGLOWEK_TEMPLATE = r"04[\.\-]05[\.\-]2020"
    for m in re.finditer(r"(\d{1,2})[\.\-](\d{2})[\.\-](\d{2,4})[rRnN\.]?", text):
        pelna = m.group(0)
        if re.search(NAGLOWEK_TEMPLATE, pelna):
            continue
        dzien, miesiac, rok = m.group(1), m.group(2), m.group(3)
        if len(rok) == 2:
            rok = "20" + rok
        try:
            if 1 <= int(dzien) <= 31 and 1 <= int(miesiac) <= 12 and 2020 <= int(rok) <= 2035:
                return f"{dzien.zfill(2)}.{miesiac}.{rok}"
        except ValueError:
            continue
    return ""

ZNANE_LOKALIZACJE = [
    "KWK Janina", "KWK Ziemowit", "KWK Piast", "KWK Murcki", "KWK Pniówek",
    "KWK Budryk", "KWK Bielszowice", "KWK Mysłowice", "KWK Bolesław Śmiały",
    "Dwory Terminal", "Terminal Dwory",
    "Elektrownia Jaworzno", "Elektrownia Łagisza", "Elektrownia Siersza",
    "Elektrownia Rybnik", "Elektrownia Połaniec",
]

def lokalizacja_z_ocr(text: str) -> str:
    upper = text.upper()

    # 1. Znane lokalizacje (najwyższy priorytet)
    for lok in ZNANE_LOKALIZACJE:
        if lok.upper() in upper:
            return lok

    # 2. Pole "Stacja / Bocznica" (Mw 581)
    m = re.search(
        r"(?:Stacja|Bocznica|Stacja\s*/\s*Bocznica)[\s\.\:\-]{0,5}([^\n\r]{3,50})",
        text, re.IGNORECASE,
    )
    if m:
        kandydat = re.split(r"\s+(?:Data|Numer)\b", m.group(1), flags=re.IGNORECASE)[0].strip().rstrip(".,")
        if len(kandydat) >= 3:
            return kandydat

    # 3. Pole "Miejscowość Stacja" (starszy formularz DDU/P3)
    m2 = re.search(
        r"(?:Miejscowo[sś][cć]|Stacja|Warsztat)[\s\.\:\/\-]{0,10}([^\n\r]{3,50})",
        text, re.IGNORECASE,
    )
    if m2:
        kandydat = re.split(r"\s+(?:Data|Numer)\b", m2.group(1), flags=re.IGNORECASE)[0].strip().rstrip(".,")
        if len(kandydat) >= 3:
            return kandydat

    # 4. KWK + nazwa (fallback)
    m3 = re.search(r"KWK\s+([A-ZŁÓŚĄĆĘŹŻa-ząćęłńóśźż]{2,}(?:\s+[A-Za-ząćęłńóśźż]+)?)", text)
    if m3:
        return ("KWK " + m3.group(1).strip()).title().replace("Kwk", "KWK")

    return ""


# ===========================================================================
# OBSŁUGA PDF
# ===========================================================================

def ocr_strony(page, dpi: int = 300) -> str:
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes())).convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    return pytesseract.image_to_string(img, lang="pol", config="--psm 6 --oem 1")

def znajdz_strone_ddu(doc) -> int:
    if len(doc) == 1:
        return 0
    for i in range(len(doc) - 1, max(len(doc) - 9, -1), -1):
        pix = doc[i].get_pixmap(dpi=100)
        img = Image.open(io.BytesIO(pix.tobytes()))
        tekst_quick = pytesseract.image_to_string(img, lang="pol")
        upper = tekst_quick.upper()
        if "DOPUSZCZENIE" in upper or ("PROTOKÓŁ" in upper and "P6" in upper):
            return i
    return len(doc) - 1

def renderuj_podglad(page, dpi: int = 150) -> bytes:
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")


# ===========================================================================
# GŁÓWNA LOGIKA PRZETWARZANIA
# ===========================================================================

def przetworz_pdf(pdf_bytes: bytes, filename: str, tryb_reczny: str = "AUTO") -> list:
    """
    Zwraca listę rekordów.
    P3  → jeden rekord (jeden wagon, numer dopuszczenia).
    DDU → jeden rekord na każdy wagon znaleziony w tabeli.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_stron = len(doc)
    ddu_idx = znajdz_strone_ddu(doc)
    podglad_bytes = renderuj_podglad(doc[ddu_idx], dpi=150)
    ddu_text = ocr_strony(doc[ddu_idx], dpi=300)
    doc.close()

    typ = tryb_reczny if tryb_reczny != "AUTO" else wykryj_typ(ddu_text)
    data = data_z_ocr(ddu_text)
    lokalizacja = lokalizacja_z_ocr(ddu_text)

    base = dict(
        filename=filename, typ=typ, data=data, lokalizacja=lokalizacja,
        ddu_strona=ddu_idx + 1, n_stron=n_stron,
        podglad_png=podglad_bytes, ocr_tekst=ddu_text,
        wyslano=False, blad="",
    )

    rekordy = []

    if typ == "P3":
        wagon = wagon_z_nazwy_pliku(filename) or wagon_z_ocr(ddu_text)
        rekordy.append({**base, "wagon": wagon, "nr_dop": nr_dop_z_ocr(ddu_text)})

    else:  # DDU
        wagony = wszystkie_wagony_z_ocr(ddu_text) or (
            [wagon_z_nazwy_pliku(filename)] if wagon_z_nazwy_pliku(filename) else []
        )
        if wagony:
            for w in wagony:
                rekordy.append({**base, "wagon": w, "nr_dop": ""})
        else:
            rekordy.append({**base, "wagon": "", "nr_dop": "",
                            "blad": "Nie znaleziono numerów wagonów"})

    return rekordy


# ===========================================================================
# SESSION STATE
# ===========================================================================
if "wyniki" not in st.session_state:
    st.session_state.wyniki = []
if "edytowany_idx" not in st.session_state:
    st.session_state.edytowany_idx = None
if "tryb" not in st.session_state:
    st.session_state.tryb = "AUTO"


# ===========================================================================
# SEKCJA 1 — PRZEŁĄCZNIK TRYBU + UPLOAD
# ===========================================================================

st.markdown('<div class="card"><div class="card-header">📂 Wgraj dokumenty</div>', unsafe_allow_html=True)

# Przełącznik trybu — 3 przyciski
c_auto, c_p3, c_ddu, _ = st.columns([1.1, 0.9, 1.7, 3.5])

with c_auto:
    if st.button("🔍 AUTO", use_container_width=True,
                 type="primary" if st.session_state.tryb == "AUTO" else "secondary"):
        st.session_state.tryb = "AUTO"
        st.rerun()
with c_p3:
    if st.button("📋 P3", use_container_width=True,
                 type="primary" if st.session_state.tryb == "P3" else "secondary"):
        st.session_state.tryb = "P3"
        st.rerun()
with c_ddu:
    if st.button("🔧 DDU / P1·P2 / Mw 581", use_container_width=True,
                 type="primary" if st.session_state.tryb == "DDU" else "secondary"):
        st.session_state.tryb = "DDU"
        st.rerun()

TRYB_OPIS = {
    "AUTO": "Automatyczne rozpoznanie typu dokumentu na podstawie treści.",
    "P3":   "Przegląd P3 — jeden wagon na plik → arkusz P3.",
    "DDU":  "DDU / Mw 581 / P1·P2 — wyciąga wszystkie wagony z tabeli → arkusz DDU.",
}
tryb_kolor = {"AUTO": "#888", "P3": "#5599ff", "DDU": "#e5001a"}
st.markdown(
    f'<div style="font-size:.85rem;color:{tryb_kolor[st.session_state.tryb]};margin:8px 0 16px 0">'
    f'▶ {TRYB_OPIS[st.session_state.tryb]}</div>',
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Przeciągnij pliki PDF lub kliknij",
    type="pdf",
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

# Przetwarzanie nowych plików
if uploaded_files:
    przetworzone_nazwy = {w["filename"] for w in st.session_state.wyniki}
    nowe = [f for f in uploaded_files if f.name not in przetworzone_nazwy]

    if nowe:
        st.markdown(f'<div class="section-label">Przetwarzam {len(nowe)} plik(ów)...</div>', unsafe_allow_html=True)
        pasek = st.progress(0)
        ph = st.empty()

        for i, plik in enumerate(nowe):
            ph.markdown(
                f'<div class="section-label">⚙️ OCR: <strong style="color:#fff">{plik.name}</strong> ({i+1}/{len(nowe)})</div>',
                unsafe_allow_html=True,
            )
            try:
                rekordy = przetworz_pdf(plik.read(), plik.name, st.session_state.tryb)
                st.session_state.wyniki.extend(rekordy)
            except Exception as e:
                st.session_state.wyniki.append(dict(
                    filename=plik.name, typ="?",
                    wagon="", nr_dop="", data="", lokalizacja="",
                    ddu_strona=0, n_stron=0,
                    podglad_png=None, ocr_tekst="",
                    wyslano=False, blad=str(e),
                ))
            pasek.progress((i + 1) / len(nowe))
            time.sleep(0.05)

        ph.empty()
        pasek.empty()


# ===========================================================================
# SEKCJA 2 — DASHBOARD + TABELA
# ===========================================================================
wyniki = st.session_state.wyniki

if wyniki:
    n_p3      = sum(1 for w in wyniki if w["typ"] == "P3")
    n_ddu     = sum(1 for w in wyniki if w["typ"] == "DDU")
    n_ok      = sum(1 for w in wyniki if w["wagon"] and not w["blad"])
    n_prob    = sum(1 for w in wyniki if not w["wagon"] or w["blad"])
    n_wyslano = sum(1 for w in wyniki if w["wyslano"])

    cols_m = st.columns(6)
    cols_m[0].metric("Rekordów", len(wyniki))
    cols_m[1].metric("Typ P3",   n_p3)
    cols_m[2].metric("Typ DDU",  n_ddu)
    cols_m[3].metric("Gotowe",   n_ok)
    cols_m[4].metric("Korekta",  n_prob)
    cols_m[5].metric("Wysłano",  n_wyslano)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-header">📋 Wyniki skanowania</div>', unsafe_allow_html=True)

    hdr = st.columns([0.35, 1.9, 0.65, 1.5, 1.0, 1.6, 1.0, 0.85, 0.65])
    for col, h in zip(hdr, ["#", "Plik", "Typ", "Wagon", "Nr dop.", "Lokalizacja", "Data", "Status", "✏️"]):
        col.markdown(f'<div class="section-label">{h}</div>', unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0 8px 0'>", unsafe_allow_html=True)

    for idx, w in enumerate(wyniki):
        c = st.columns([0.35, 1.9, 0.65, 1.5, 1.0, 1.6, 1.0, 0.85, 0.65])
        c[0].markdown(f'<div style="color:#555;padding-top:8px">{idx+1}</div>', unsafe_allow_html=True)
        strip = "type-strip-p3" if w["typ"] == "P3" else "type-strip-ddu"
        c[1].markdown(f'<div class="{strip} filename-cell" style="padding-top:6px">{w["filename"]}</div>', unsafe_allow_html=True)
        tb = '<span class="badge badge-p3">P3</span>' if w["typ"] == "P3" else '<span class="badge badge-ddu">DDU</span>'
        c[2].markdown(f'<div style="padding-top:6px">{tb}</div>', unsafe_allow_html=True)
        c[3].markdown(f'<div class="wagon-num" style="padding-top:6px">{w["wagon"] or "—"}</div>', unsafe_allow_html=True)
        c[4].markdown(f'<div style="color:#ccc;padding-top:6px;font-size:.85rem">{w["nr_dop"] or "—"}</div>', unsafe_allow_html=True)
        c[5].markdown(f'<div style="color:#ccc;padding-top:6px;font-size:.85rem">{w["lokalizacja"] or "—"}</div>', unsafe_allow_html=True)
        c[6].markdown(f'<div style="color:#ccc;padding-top:6px;font-size:.85rem">{w["data"] or "—"}</div>', unsafe_allow_html=True)

        if w["blad"]:
            sb = '<span class="badge badge-error">Błąd</span>'
        elif w["wyslano"]:
            sb = '<span class="badge badge-sent">Wysłano</span>'
        elif w["wagon"]:
            sb = '<span class="badge badge-ok">OK</span>'
        else:
            sb = '<span class="badge badge-warn">Korekta</span>'
        c[7].markdown(f'<div style="padding-top:6px">{sb}</div>', unsafe_allow_html=True)

        with c[8]:
            if st.button("✏️", key=f"edit_{idx}", help="Edytuj / wyślij"):
                st.session_state.edytowany_idx = idx

        st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- BATCH WYŚLIJ ----
    gotowe_p3  = [(i, w) for i, w in enumerate(wyniki) if w["wagon"] and not w["wyslano"] and not w["blad"] and w["typ"] == "P3"]
    gotowe_ddu = [(i, w) for i, w in enumerate(wyniki) if w["wagon"] and not w["wyslano"] and not w["blad"] and w["typ"] == "DDU"]

    if gotowe_p3 or gotowe_ddu:
        st.markdown("<br>", unsafe_allow_html=True)
        c_send, c_clear = st.columns([3, 1])

        with c_send:
            parts = []
            if gotowe_p3:  parts.append(f"{len(gotowe_p3)}×P3")
            if gotowe_ddu: parts.append(f"{len(gotowe_ddu)}×DDU")

            if st.button(f"🚀 WYŚLIJ WSZYSTKIE GOTOWE ({' + '.join(parts)})",
                         type="primary", use_container_width=True):
                try:
                    client = get_google_client()

                    if gotowe_p3 and ARKUSZ_P3_URL:
                        sheet_p3 = client.open_by_url(ARKUSZ_P3_URL).sheet1
                        lp = 1 if len(sheet_p3.col_values(1)) <= 1 else int(sheet_p3.col_values(1)[-1]) + 1
                        rows = []
                        for offset, (i, w) in enumerate(gotowe_p3):
                            rows.append([lp + offset, w["nr_dop"], w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sheet_p3.append_rows(rows)

                    if gotowe_ddu and ARKUSZ_DDU_URL:
                        sheet_ddu = client.open_by_url(ARKUSZ_DDU_URL).sheet1
                        lp = 1 if len(sheet_ddu.col_values(1)) <= 1 else int(sheet_ddu.col_values(1)[-1]) + 1
                        rows = []
                        for offset, (i, w) in enumerate(gotowe_ddu):
                            rows.append([lp + offset, w["lokalizacja"], w["data"], w["wagon"]])
                            st.session_state.wyniki[i]["wyslano"] = True
                        sheet_ddu.append_rows(rows)

                    st.success(f"✅ Wysłano {len(gotowe_p3)} ×P3 i {len(gotowe_ddu)} ×DDU do Google Sheets!")
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Błąd: {e}")

        with c_clear:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("🗑️ Wyczyść listę", use_container_width=True):
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
            f'<div class="card"><div class="card-header">✏️ Edycja — {w["filename"]} '
            f'<span style="font-size:.75rem;color:#666">[Typ: {w["typ"]}]</span></div>',
            unsafe_allow_html=True,
        )

        col_img, col_form = st.columns([1, 1], gap="large")

        with col_img:
            st.markdown('<div class="section-label">Strona DDU</div>', unsafe_allow_html=True)
            if w["podglad_png"]:
                st.image(w["podglad_png"], use_container_width=True)
                st.caption(f'Strona {w["ddu_strona"]} z {w["n_stron"]}')
            else:
                st.warning("Brak podglądu")
            with st.expander("🔍 Surowy tekst OCR"):
                st.code(w.get("ocr_tekst", ""), language=None)

        with col_form:
            st.markdown('<div class="section-label">Dane do rejestru</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            new_typ = st.selectbox("Typ dokumentu", ["P3", "DDU"],
                                   index=0 if w["typ"] == "P3" else 1,
                                   key=f"sel_typ_{idx}")
            wagon_val  = st.text_input("🚂 Numer wagonu *", value=w["wagon"],
                                       placeholder="np. 3351 6666 408-6", key=f"w_wagon_{idx}")
            nr_dop_val = ""
            if new_typ == "P3":
                nr_dop_val = st.text_input("📑 Numer dopuszczenia", value=w["nr_dop"],
                                           placeholder="np. 17044086", key=f"w_nrdop_{idx}")
            data_val = st.text_input("📅 Data wystawienia", value=w["data"],
                                     placeholder="np. 17.04.2026", key=f"w_data_{idx}")
            lok_val  = st.text_input("📍 Miejscowość / Zakład", value=w["lokalizacja"],
                                     placeholder="np. KWK Janina", key=f"w_lok_{idx}")

            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)

            with c1:
                if st.button("💾 Zapisz zmiany", key=f"save_{idx}", use_container_width=True):
                    st.session_state.wyniki[idx].update(
                        typ=new_typ, wagon=wagon_val, nr_dop=nr_dop_val,
                        data=data_val, lokalizacja=lok_val, blad="",
                    )
                    st.success("Zapisano!")

            with c2:
                if st.button("✅ Wyślij ten wpis", key=f"send_{idx}",
                             use_container_width=True, type="primary"):
                    if not wagon_val.strip():
                        st.error("❌ Numer wagonu jest wymagany!")
                    else:
                        try:
                            client = get_google_client()
                            url = ARKUSZ_P3_URL if new_typ == "P3" else ARKUSZ_DDU_URL
                            sheet = client.open_by_url(url).sheet1
                            lp_col = sheet.col_values(1)
                            lp = 1 if len(lp_col) <= 1 else int(lp_col[-1]) + 1

                            if new_typ == "P3":
                                sheet.append_rows([[lp, nr_dop_val, lok_val, data_val, wagon_val.strip()]])
                            else:
                                sheet.append_rows([[lp, lok_val, data_val, wagon_val.strip()]])

                            st.session_state.wyniki[idx].update(
                                typ=new_typ, wagon=wagon_val, nr_dop=nr_dop_val,
                                data=data_val, lokalizacja=lok_val,
                                wyslano=True, blad="",
                            )
                            st.success(f"✅ LP={lp} → arkusz {new_typ}")
                            st.balloons()
                            st.session_state.edytowany_idx = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✖ Zamknij panel", key=f"close_{idx}"):
                st.session_state.edytowany_idx = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# ===========================================================================
# STOPKA
# ===========================================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#333;font-size:.75rem;font-family:'Barlow Condensed',sans-serif;letter-spacing:2px;text-transform:uppercase;">
  KORCZ Serwis Pojazdów Kolejowych &nbsp;|&nbsp; v3.0 &nbsp;|&nbsp;
  P3 → <span style="color:#5599ff">Arkusz P3</span> &nbsp;·&nbsp;
  DDU / Mw 581 / P1·P2 → <span style="color:#e5001a">Arkusz DDU</span>
</div>
""", unsafe_allow_html=True)
