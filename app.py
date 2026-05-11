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

  /* Reset i tło */
  .stApp {
    background-color: #0d0d0d;
    font-family: 'Barlow', sans-serif;
  }

  /* Ukryj domyślny header Streamlit */
  header[data-testid="stHeader"] { background: transparent; }
  #MainMenu, footer { visibility: hidden; }

  /* ---- HEADER KORCZ ---- */
  .korcz-header {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 20px 0 16px 0;
    border-bottom: 3px solid #e5001a;
    margin-bottom: 32px;
  }
  .korcz-logo-text {
    font-family: 'Barlow Condensed', sans-serif;
  }
  .korcz-logo-text .brand { font-size: 2.6rem; font-weight: 900; color: #e5001a; letter-spacing: 2px; line-height: 1; }
  .korcz-logo-text .sub   { font-size: 1rem; font-weight: 600; color: #cccccc; letter-spacing: 3px; text-transform: uppercase; }

  /* ---- KARTY ---- */
  .card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .card-header {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e5001a;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2a2a2a;
  }

  /* ---- BADGE STATUSU ---- */
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 2px;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: 'Barlow Condensed', sans-serif;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .badge-ok      { background: #003d1a; color: #00d455; border: 1px solid #00d455; }
  .badge-warn    { background: #3d2200; color: #ffa500; border: 1px solid #ffa500; }
  .badge-error   { background: #3d0008; color: #ff4060; border: 1px solid #ff4060; }
  .badge-pending { background: #1a1a2e; color: #7090ff; border: 1px solid #7090ff; }

  /* ---- TABELA WYNIKÓW ---- */
  .results-table { width: 100%; border-collapse: collapse; }
  .results-table th {
    background: #111;
    color: #888;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid #2a2a2a;
  }
  .results-table td {
    padding: 12px 12px;
    border-bottom: 1px solid #1f1f1f;
    color: #ddd;
    font-size: 0.9rem;
    vertical-align: middle;
  }
  .results-table tr:hover td { background: #1f1f1f; }
  .wagon-num { font-family: 'Barlow Condensed', sans-serif; font-size: 1.05rem; color: #fff; font-weight: 700; }
  .filename-cell { color: #888; font-size: 0.8rem; }

  /* ---- INPUTS ---- */
  .stTextInput > label { color: #aaa !important; font-size: 0.8rem !important; letter-spacing: 1px; text-transform: uppercase; }
  .stTextInput > div > div > input {
    background: #111 !important;
    border: 1px solid #333 !important;
    color: #fff !important;
    border-radius: 2px !important;
    font-family: 'Barlow', sans-serif !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #e5001a !important;
    box-shadow: 0 0 0 1px #e5001a !important;
  }

  /* ---- PRZYCISKI ---- */
  .stButton > button {
    background: #e5001a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 2px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 10px 24px !important;
    transition: background 0.15s !important;
  }
  .stButton > button:hover { background: #b30015 !important; }

  /* Secondary button */
  .btn-secondary > button {
    background: #1a1a1a !important;
    border: 1px solid #444 !important;
    color: #ccc !important;
  }
  .btn-secondary > button:hover { border-color: #e5001a !important; color: #fff !important; }

  /* ---- FILE UPLOADER ---- */
  [data-testid="stFileUploader"] {
    background: #111 !important;
    border: 2px dashed #333 !important;
    border-radius: 4px !important;
    padding: 24px !important;
    transition: border-color 0.2s;
  }
  [data-testid="stFileUploader"]:hover { border-color: #e5001a !important; }
  [data-testid="stFileUploader"] label { color: #888 !important; }

  /* ---- PROGRESS / SPINNER ---- */
  .stProgress > div > div > div { background: #e5001a !important; }

  /* ---- DIVIDER ---- */
  hr { border-color: #2a2a2a !important; }

  /* ---- EXPANDER ---- */
  .streamlit-expanderHeader {
    background: #111 !important;
    color: #888 !important;
    font-size: 0.8rem !important;
    border-radius: 2px !important;
  }

  /* ---- METRIC ---- */
  [data-testid="stMetric"] { background: #111; border: 1px solid #2a2a2a; border-radius: 4px; padding: 16px; }
  [data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.75rem !important; letter-spacing: 1px; text-transform: uppercase; }
  [data-testid="stMetricValue"] { color: #fff !important; font-family: 'Barlow Condensed', sans-serif !important; font-size: 2rem !important; }

  /* ---- TABS ---- */
  .stTabs [data-baseweb="tab-list"] { background: #0d0d0d; border-bottom: 2px solid #2a2a2a; }
  .stTabs [data-baseweb="tab"] { color: #666; font-family: 'Barlow Condensed', sans-serif; font-size: 1rem; letter-spacing: 1px; text-transform: uppercase; }
  .stTabs [aria-selected="true"] { color: #e5001a !important; border-bottom: 2px solid #e5001a !important; }

  /* ---- ALERT / SUCCESS ---- */
  .stAlert { border-radius: 2px !important; }

  /* Licznik plików */
  .file-count {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 3.5rem;
    font-weight: 900;
    color: #e5001a;
    line-height: 1;
  }

  /* Separator pionowy */
  .v-sep { border-left: 1px solid #2a2a2a; height: 100%; }

  /* Nagłówek sekcji */
  .section-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 4px;
  }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# LOGO KORCZ — z pliku PNG (base64) lub fallback tekstowy
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
    <div class="sub">Skaner DDU / Przegląd P3</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# POŁĄCZENIE Z GOOGLE SHEETS
# ---------------------------------------------------------------------------
ARKUSZ_URL = "https://docs.google.com/spreadsheets/d/1Np2uu4NI7cJ2vYeNuC57ugAQ0wKsvN5gPqUqY745Ikw/edit?usp=sharing"

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
# FUNKCJE POMOCNICZE — EKSTRAKCJA DANYCH (bez zmian logicznych)
# ===========================================================================

def formatuj_wagon(cyfry_12: str) -> str:
    d = cyfry_12
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}"

def wagon_z_nazwy_pliku(filename: str) -> str:
    m = re.search(r"(\d{4})[\s_\-]?(\d{4})[\s_\-]?(\d{3})[\s_\-](\d)", filename)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)
    return ""

def wagon_z_ocr(text: str) -> str:
    m = re.search(r"(\d{4})[\s\.,]{1,4}(\d{4})[\s\.,]{1,4}(\d{3})[\s\-](\d)", text)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)
    m2 = re.search(r"wagon[ou][\s\.\:\-]{0,30}([\d\s,\.\-]{10,30})", text, re.IGNORECASE)
    if m2:
        cyfry = re.findall(r"\d", m2.group(1))
        if len(cyfry) >= 12:
            return formatuj_wagon("".join(cyfry[:12]))
    return ""

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
        if 1 <= int(dzien) <= 31 and 1 <= int(miesiac) <= 12:
            return f"{dzien.zfill(2)}.{miesiac}.{rok}"
    return ""

def lokalizacja_z_ocr(text: str) -> str:
    m = re.search(r"KWK\s+([A-ZŁÓŚĄĆĘŹŻa-ząćęłńóśźż]{2,}(?:\s+[A-Za-ząćęłńóśźż]+)?)", text)
    if m:
        return ("KWK " + m.group(1).strip()).title().replace("Kwk", "KWK")
    m2 = re.search(
        r"([A-ZŁÓŚĄĆĘŹŻ][A-Za-ząćęłńóśźżŁÓŚĄĆĘŹŻ ]{3,30})\s+\d{1,2}[\.\-]\d{2}[\.\-]\d{2}", text)
    if m2:
        kandydat = m2.group(1).strip()
        SZUM = {"Serwis", "Marcin", "Sylwester", "Kercz", "Inter", "Komtrans"}
        if not any(s in kandydat for s in SZUM):
            return kandydat
    return ""


# ===========================================================================
# FUNKCJE OBSŁUGI PDF
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

def przetworz_pdf(pdf_bytes: bytes, filename: str) -> dict:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_stron = len(doc)
    ddu_idx = znajdz_strone_ddu(doc)
    podglad_bytes = renderuj_podglad(doc[ddu_idx], dpi=150)
    ddu_text = ocr_strony(doc[ddu_idx], dpi=300)
    doc.close()

    wagon = wagon_z_nazwy_pliku(filename) or wagon_z_ocr(ddu_text)
    nr_dop = nr_dop_z_ocr(ddu_text)
    data = data_z_ocr(ddu_text)
    lokalizacja = lokalizacja_z_ocr(ddu_text)

    return {
        "filename": filename,
        "wagon": wagon,
        "nr_dop": nr_dop,
        "data": data,
        "lokalizacja": lokalizacja,
        "ddu_strona": ddu_idx + 1,
        "n_stron": n_stron,
        "podglad_png": podglad_bytes,
        "ocr_tekst": ddu_text,
        "wyslano": False,
        "blad": "",
    }


# ===========================================================================
# SESSION STATE — przechowuje wyniki między interakcjami
# ===========================================================================
if "wyniki" not in st.session_state:
    st.session_state.wyniki = []   # lista słowników z danymi

if "edytowany_idx" not in st.session_state:
    st.session_state.edytowany_idx = None


# ===========================================================================
# SEKCJA 1 — UPLOAD PLIKÓW
# ===========================================================================

st.markdown('<div class="card"><div class="card-header">📂 Wgraj dokumenty</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Przeciągnij pliki PDF lub kliknij — DDU (1 str.) lub Przeglądy P3 (wielostronicowe)",
    type="pdf",
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_files:
    # Filtruj tylko nowe pliki (nieprzetworzone jeszcze)
    przetworzone_nazwy = {w["filename"] for w in st.session_state.wyniki}
    nowe = [f for f in uploaded_files if f.name not in przetworzone_nazwy]

    if nowe:
        st.markdown(f'<div class="section-label">Przetwarzam {len(nowe)} nowy/nowych plik(ów)...</div>', unsafe_allow_html=True)
        pasek = st.progress(0)
        placeholder_status = st.empty()

        for i, plik in enumerate(nowe):
            placeholder_status.markdown(
                f'<div class="section-label">⚙️ OCR: <strong style="color:#fff">{plik.name}</strong> ({i+1}/{len(nowe)})</div>',
                unsafe_allow_html=True
            )
            try:
                dane = przetworz_pdf(plik.read(), plik.name)
                st.session_state.wyniki.append(dane)
            except Exception as e:
                st.session_state.wyniki.append({
                    "filename": plik.name,
                    "wagon": "", "nr_dop": "", "data": "", "lokalizacja": "",
                    "ddu_strona": 0, "n_stron": 0,
                    "podglad_png": None, "ocr_tekst": "",
                    "wyslano": False, "blad": str(e),
                })
            pasek.progress((i + 1) / len(nowe))
            time.sleep(0.05)

        placeholder_status.empty()
        pasek.empty()


# ===========================================================================
# SEKCJA 2 — DASHBOARD WYNIKÓW
# ===========================================================================

wyniki = st.session_state.wyniki

if wyniki:
    # Metryki zbiorcze
    n_ok      = sum(1 for w in wyniki if w["wagon"] and not w["blad"])
    n_warn    = sum(1 for w in wyniki if not w["wagon"] and not w["blad"])
    n_blad    = sum(1 for w in wyniki if w["blad"])
    n_wyslano = sum(1 for w in wyniki if w["wyslano"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Łącznie", len(wyniki))
    m2.metric("Gotowe", n_ok)
    m3.metric("Wymaga korekty", n_warn)
    m4.metric("Wysłano do rejestru", n_wyslano)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- TABELA WYNIKÓW ----
    st.markdown('<div class="card"><div class="card-header">📋 Wyniki skanowania</div>', unsafe_allow_html=True)

    # Nagłówek tabeli
    header_cols = st.columns([0.4, 2.2, 1.5, 1.2, 1.6, 1.2, 0.8, 0.8])
    for col, h in zip(header_cols, ["#", "Plik", "Wagon", "Nr dop.", "Lokalizacja", "Data", "Status", "Akcja"]):
        col.markdown(f'<div class="section-label">{h}</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin:4px 0 8px 0'>", unsafe_allow_html=True)

    for idx, w in enumerate(wyniki):
        cols = st.columns([0.4, 2.2, 1.5, 1.2, 1.6, 1.2, 0.8, 0.8])

        # Numer
        cols[0].markdown(f'<div style="color:#666;font-size:0.9rem;padding-top:8px">{idx+1}</div>', unsafe_allow_html=True)

        # Nazwa pliku
        cols[1].markdown(
            f'<div class="filename-cell" style="padding-top:8px;word-break:break-all">{w["filename"]}</div>',
            unsafe_allow_html=True
        )

        # Wagon
        cols[2].markdown(
            f'<div class="wagon-num" style="padding-top:8px">{w["wagon"] or "—"}</div>',
            unsafe_allow_html=True
        )

        # Nr dopuszczenia
        cols[3].markdown(
            f'<div style="color:#ccc;padding-top:8px;font-size:0.9rem">{w["nr_dop"] or "—"}</div>',
            unsafe_allow_html=True
        )

        # Lokalizacja
        cols[4].markdown(
            f'<div style="color:#ccc;padding-top:8px;font-size:0.9rem">{w["lokalizacja"] or "—"}</div>',
            unsafe_allow_html=True
        )

        # Data
        cols[5].markdown(
            f'<div style="color:#ccc;padding-top:8px;font-size:0.9rem">{w["data"] or "—"}</div>',
            unsafe_allow_html=True
        )

        # Status badge
        if w["blad"]:
            badge = '<span class="badge badge-error">Błąd</span>'
        elif w["wyslano"]:
            badge = '<span class="badge badge-ok">Wysłano</span>'
        elif w["wagon"]:
            badge = '<span class="badge badge-ok">OK</span>'
        else:
            badge = '<span class="badge badge-warn">Korekta</span>'
        cols[6].markdown(f'<div style="padding-top:8px">{badge}</div>', unsafe_allow_html=True)

        # Przycisk edycji / podglądu
        with cols[7]:
            if st.button("✏️", key=f"edit_{idx}", help="Edytuj i wyślij"):
                st.session_state.edytowany_idx = idx

        st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- BATCH: WYŚLIJ WSZYSTKIE GOTOWE ----
    gotowe_do_wyslania = [
        (i, w) for i, w in enumerate(wyniki)
        if w["wagon"] and not w["wyslano"] and not w["blad"]
    ]

    if gotowe_do_wyslania:
        st.markdown("<br>", unsafe_allow_html=True)
        col_batch, col_clear = st.columns([2, 1])

        with col_batch:
            if st.button(
                f"🚀 WYŚLIJ WSZYSTKIE GOTOWE ({len(gotowe_do_wyslania)} pliki)",
                type="primary",
                use_container_width=True,
            ):
                try:
                    client = get_google_client()
                    sheet = client.open_by_url(ARKUSZ_URL).sheet1
                    wszystkie_lp = sheet.col_values(1)
                    lp_start = 1 if len(wszystkie_lp) <= 1 else int(wszystkie_lp[-1]) + 1

                    rows = []
                    for offset, (i, w) in enumerate(gotowe_do_wyslania):
                        rows.append([
                            lp_start + offset,
                            w["nr_dop"],
                            w["lokalizacja"],
                            w["data"],
                            w["wagon"],
                        ])
                        st.session_state.wyniki[i]["wyslano"] = True

                    sheet.append_rows(rows)
                    st.success(f"✅ Wysłano {len(rows)} wpisów do Google Sheets!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Błąd połączenia z Arkuszem: {e}")

        with col_clear:
            with st.container():
                st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
                if st.button("🗑️ Wyczyść listę", use_container_width=True):
                    st.session_state.wyniki = []
                    st.session_state.edytowany_idx = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


# ===========================================================================
# SEKCJA 3 — PANEL EDYCJI (dla wybranego pliku)
# ===========================================================================

if st.session_state.edytowany_idx is not None and wyniki:
    idx = st.session_state.edytowany_idx
    if idx < len(wyniki):
        w = wyniki[idx]

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="card"><div class="card-header">✏️ Edycja — {w["filename"]}</div>',
            unsafe_allow_html=True
        )

        col_img, col_form = st.columns([1, 1], gap="large")

        with col_img:
            st.markdown('<div class="section-label">Strona DDU</div>', unsafe_allow_html=True)
            if w["podglad_png"]:
                st.image(w["podglad_png"], use_container_width=True)
                st.caption(f'Strona {w["ddu_strona"]} z {w["n_stron"]}')
            else:
                st.warning("Brak podglądu (błąd przetwarzania)")

            if w["ocr_tekst"]:
                with st.expander("🔍 Surowy tekst OCR"):
                    st.code(w["ocr_tekst"], language=None)

        with col_form:
            st.markdown('<div class="section-label">Dane do rejestru</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            wagon_val = st.text_input("🚂 Numer wagonu *", value=w["wagon"],
                                      placeholder="np. 3351 6666 408-6", key=f"w_wagon_{idx}")
            nr_dop_val = st.text_input("📑 Numer dopuszczenia", value=w["nr_dop"],
                                       placeholder="np. 17044086", key=f"w_nrdop_{idx}")
            data_val = st.text_input("📅 Data wystawienia", value=w["data"],
                                     placeholder="np. 17.04.2026", key=f"w_data_{idx}")
            lok_val = st.text_input("📍 Miejscowość / Zakład", value=w["lokalizacja"],
                                    placeholder="np. KWK Piast", key=f"w_lok_{idx}")

            st.markdown("<br>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Zapisz zmiany", key=f"save_{idx}", use_container_width=True):
                    st.session_state.wyniki[idx].update({
                        "wagon": wagon_val,
                        "nr_dop": nr_dop_val,
                        "data": data_val,
                        "lokalizacja": lok_val,
                    })
                    st.success("Zapisano!")

            with c2:
                if st.button("✅ Wyślij ten wpis", key=f"send_{idx}", use_container_width=True, type="primary"):
                    if not wagon_val.strip():
                        st.error("❌ Numer wagonu jest wymagany!")
                    else:
                        try:
                            client = get_google_client()
                            sheet = client.open_by_url(ARKUSZ_URL).sheet1
                            wszystkie_lp = sheet.col_values(1)
                            lp = 1 if len(wszystkie_lp) <= 1 else int(wszystkie_lp[-1]) + 1
                            sheet.append_rows([[lp, nr_dop_val, lok_val, data_val, wagon_val.strip()]])
                            st.session_state.wyniki[idx].update({
                                "wagon": wagon_val, "nr_dop": nr_dop_val,
                                "data": data_val, "lokalizacja": lok_val,
                                "wyslano": True,
                            })
                            st.success(f"✅ LP={lp} wysłano!")
                            st.balloons()
                            st.session_state.edytowany_idx = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Błąd: {e}")

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
<div style="text-align:center;color:#333;font-size:0.75rem;font-family:'Barlow Condensed',sans-serif;letter-spacing:2px;text-transform:uppercase;">
  KORCZ Serwis Pojazdów Kolejowych &nbsp;|&nbsp; Skaner DDU/P3 v2.0
</div>
""", unsafe_allow_html=True)
