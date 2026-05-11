import streamlit as st
import fitz  # PyMuPDF
from google.cloud import vision
from google.oauth2.service_account import Credentials
import io
import re
import gspread

# ---------------------------------------------------------------------------
# KONFIGURACJA STRONY
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Skaner DDU / P3 — Google Vision", layout="wide")
st.title("🚀 Skaner Dopuszczeń P3 — Google Cloud Vision")
st.markdown(
    "Wgraj DDU (1 strona) lub pełny Przegląd P3. "
    "Program znajdzie stronę dopuszczenia, odczyta pismo ręczne przez Google AI "
    "i pozwoli Ci sprawdzić dane przed zapisem do rejestru."
)

# ---------------------------------------------------------------------------
# !!! WKLEJ TUTAJ LINK DO SWOJEGO ARKUSZA !!!
# ---------------------------------------------------------------------------
ARKUSZ_URL = "TWÓJ_LINK_DO_ARKUSZA_GOOGLE"

# ---------------------------------------------------------------------------
# KLIENTY — GOOGLE VISION + GOOGLE SHEETS
# ---------------------------------------------------------------------------

@st.cache_resource
def get_vision_client():
    """Klient Google Cloud Vision — używa tego samego konta usługi co Sheets."""
    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/cloud-vision"],
    )
    return vision.ImageAnnotatorClient(credentials=creds)


@st.cache_resource
def get_sheets_client():
    """Klient Google Sheets."""
    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def ocr_vision(image_bytes: bytes) -> str:
    """
    Wysyła obraz do Google Cloud Vision API (DOCUMENT_TEXT_DETECTION).
    Ten model jest zoptymalizowany pod kątem formularzy z pismem ręcznym.
    Zwraca pełny tekst strony.
    """
    client = get_vision_client()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"Google Vision API error: {response.error.message}")
    return response.full_text_annotation.text if response.full_text_annotation else ""


# ===========================================================================
# EKSTRAKCJA DANYCH — NAPRAWIONE FUNKCJE
# ===========================================================================

def formatuj_wagon(cyfry_12: str) -> str:
    """12 cyfr → 'XXXX XXXX XXX-X'"""
    d = cyfry_12
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}"


def wagon_z_nazwy_pliku(filename: str) -> str:
    """
    STRATEGIA 1 — najniezawodniejsza.
    Wyciąga numer wagonu z nazwy pliku.
    Działa dla: Przegląd_P3_33516666408-6.pdf
    """
    m = re.search(r"(\d{4})[\s_\-]?(\d{4})[\s_\-]?(\d{3})[\s_\-](\d)", filename)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)
    return ""


def wagon_z_tekstu(text: str) -> str:
    """
    STRATEGIA 2 — z tekstu OCR.
    Google Vision poprawnie odczytuje numer wagonu, więc szukamy wzorca.
    NIE używamy metody 'sklej wszystkie cyfry' — ona wybiera datę z nagłówka!
    """
    # Wzorzec z separatorami: 3351 6666 408-6 lub 33516666408-6
    m = re.search(r"(\d{4})[\s\.,]{0,3}(\d{4})[\s\.,]{0,3}(\d{3})[\s\-](\d)", text)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)

    # Fallback: szukaj cyfr przy słowie 'wagonu'
    m2 = re.search(
        r"wagon[ou][\s\.\:\-]{0,30}([\d\s,\.\-]{10,30})", text, re.IGNORECASE
    )
    if m2:
        cyfry = re.findall(r"\d", m2.group(1))
        if len(cyfry) >= 12:
            return formatuj_wagon("".join(cyfry[:12]))

    return ""


def nr_dop_z_tekstu(text: str) -> str:
    """
    Szuka numeru dopuszczenia przy słowie 'Nr'.
    Google Vision poprawnie czyta odręczne '1704 4086'.
    """
    m = re.search(r"\bNr[\.\s:]{1,5}([\d\s]{5,14})", text, re.IGNORECASE)
    if m:
        val = re.sub(r"\s", "", m.group(1)).strip()
        if 6 <= len(val) <= 12:
            return val
    return ""


def data_z_tekstu(text: str) -> str:
    """
    Szuka daty wystawienia DDU.
    POMIJA datę szablonu z nagłówka (04.05.2020r.) — ta jest na każdym formularzu.
    Obsługuje rok 2-cyfrowy (26 → 2026) i przyrostek 'r.' lub 'n.'.
    """
    TEMPLATE_DATE = r"04[\.\-]05[\.\-]2020"

    for m in re.finditer(
        r"(\d{1,2})[\.\-](\d{2})[\.\-](\d{2,4})[rRnN\.]?", text
    ):
        if re.search(TEMPLATE_DATE, m.group(0)):
            continue  # pomiń datę szablonu z nagłówka formularza

        dzien, miesiac, rok = m.group(1), m.group(2), m.group(3)
        if len(rok) == 2:
            rok = "20" + rok

        if 1 <= int(dzien) <= 31 and 1 <= int(miesiac) <= 12:
            return f"{dzien.zfill(2)}.{miesiac}.{rok}"

    return ""


def lokalizacja_z_tekstu(text: str) -> str:
    """
    Wyciąga lokalizację z linii '(miejsce i data wystawienia)'.
    Google Vision poprawnie czyta 'KWK Piast' — nie musimy się domyślać.
    """
    # Szukaj KWK + nazwa zakładu
    m = re.search(
        r"KWK\s+([A-ZŁÓŚĄĆĘŹŻa-ząćęłńóśźż]{2,}(?:\s+[A-Za-ząćęłńóśźż]+)?)", text
    )
    if m:
        return ("KWK " + m.group(1).strip()).title().replace("Kwk", "KWK")

    # Fallback: tekst przed datą na tej samej linii
    m2 = re.search(
        r"([A-ZŁÓŚĄĆĘŹŻ][A-Za-ząćęłńóśźżŁÓŚĄĆĘŹŻ ]{3,30})\s+\d{1,2}[\.\-]\d{2}[\.\-]\d{2}",
        text,
    )
    if m2:
        kandydat = m2.group(1).strip()
        SZUM = {"Serwis", "Marcin", "Sylwester", "Kercz", "Inter", "Komtrans"}
        if not any(s in kandydat for s in SZUM):
            return kandydat

    return ""


# ===========================================================================
# OBSŁUGA PDF
# ===========================================================================

def znajdz_strone_ddu(doc) -> int:
    """
    Szuka strony DDU (Protokół P6 / Dopuszczenie do użytkowania).
    Skanuje od końca — DDU jest zazwyczaj ostatnią stroną.
    Używa minimalnego DPI do szybkiego podglądu (nie Vision API).
    """
    if len(doc) == 1:
        return 0

    for i in range(len(doc) - 1, max(len(doc) - 9, -1), -1):
        # Szybki lokalny OCR na 100 DPI tylko do wykrycia strony DDU
        pix = doc[i].get_pixmap(dpi=100)
        img_bytes = pix.tobytes("png")
        # Użyj Vision API — nawet przy niskim DPI rozpozna słowo DOPUSZCZENIE
        try:
            tekst_quick = ocr_vision(img_bytes)
            if "DOPUSZCZENIE" in tekst_quick.upper():
                return i
        except Exception:
            pass  # W razie błędu API spróbuj następną stronę

    return len(doc) - 1  # Fallback: ostatnia strona


def renderuj_podglad(page, dpi: int = 150) -> bytes:
    """Renderuje stronę jako PNG do wyświetlenia w Streamlit."""
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")


def przetworz_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """
    Główna logika: znajdź stronę DDU → Vision OCR → wyciągnij dane.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_stron = len(doc)

    # 1. Znajdź stronę DDU
    with st.spinner(f"Szukam strony DDU w {n_stron}-stronicowym pliku..."):
        ddu_idx = znajdz_strone_ddu(doc)

    # 2. Podgląd (nie wysyłamy do Vision — tylko do wyświetlenia)
    podglad_bytes = renderuj_podglad(doc[ddu_idx], dpi=150)

    # 3. Wyślij stronę DDU do Google Vision API (300 DPI = optymalnie)
    with st.spinner("Wysyłam stronę DDU do Google Cloud Vision AI..."):
        pix = doc[ddu_idx].get_pixmap(dpi=300)
        ddu_text = ocr_vision(pix.tobytes("png"))

    doc.close()

    # 4. Ekstrakcja danych
    wagon = wagon_z_nazwy_pliku(filename) or wagon_z_tekstu(ddu_text)
    nr_dop = nr_dop_z_tekstu(ddu_text)
    data = data_z_tekstu(ddu_text)
    lokalizacja = lokalizacja_z_tekstu(ddu_text)

    return {
        "wagon": wagon,
        "nr_dop": nr_dop,
        "data": data,
        "lokalizacja": lokalizacja,
        "ddu_strona": ddu_idx + 1,
        "n_stron": n_stron,
        "podglad_png": podglad_bytes,
        "ocr_tekst": ddu_text,
    }


# ===========================================================================
# INTERFEJS UŻYTKOWNIKA
# ===========================================================================

uploaded_file = st.file_uploader(
    "📂 Wgraj DDU (1 strona) lub pełny Przegląd P3 (wielostronicowy PDF)",
    type="pdf",
)

if uploaded_file is not None:
    dane = przetworz_pdf(uploaded_file.read(), uploaded_file.name)

    st.divider()

    # --- Układ dwukolumnowy ---
    col_img, col_form = st.columns([1, 1], gap="large")

    with col_img:
        st.subheader("📄 Strona dopuszczenia (DDU)")
        st.caption(
            f"Plik: **{uploaded_file.name}** | "
            f"Strona DDU: **{dane['ddu_strona']}/{dane['n_stron']}**"
        )
        st.image(dane["podglad_png"], use_container_width=True)

    with col_form:
        st.subheader("✏️ Dane do rejestru")
        st.markdown("_Sprawdź dane na obrazie obok i popraw jeśli trzeba._")

        # Wskaźniki auto-wypełnienia
        def ikona(val: str) -> str:
            return "✅" if val else "⚠️"

        st.caption(
            f"{ikona(dane['wagon'])} Wagon  "
            f"{ikona(dane['nr_dop'])} Nr dopuszczenia  "
            f"{ikona(dane['data'])} Data  "
            f"{ikona(dane['lokalizacja'])} Lokalizacja"
        )

        wagon_val = st.text_input(
            "🚂 Numer wagonu *",
            value=dane["wagon"],
            placeholder="np. 3351 6666 408-6",
            help="Wymagany. Format: XXXX XXXX XXX-X",
        )
        nr_dop_val = st.text_input(
            "📑 Numer dopuszczenia",
            value=dane["nr_dop"],
            placeholder="np. 17044086",
        )
        data_val = st.text_input(
            "📅 Data wystawienia",
            value=dane["data"],
            placeholder="np. 17.04.2026",
        )
        lok_val = st.text_input(
            "📍 Miejscowość / Zakład",
            value=dane["lokalizacja"],
            placeholder="np. KWK Piast",
        )

        st.divider()

        if st.button(
            "✅ Wyślij do rejestru Google Sheets",
            type="primary",
            use_container_width=True,
        ):
            if not wagon_val.strip():
                st.error("❌ Numer wagonu jest wymagany!")
            else:
                try:
                    client = get_sheets_client()
                    sheet = client.open_by_url(ARKUSZ_URL).sheet1
                    wszystkie_lp = sheet.col_values(1)
                    lp = 1 if len(wszystkie_lp) <= 1 else int(wszystkie_lp[-1]) + 1
                    sheet.append_rows(
                        [[lp, nr_dop_val, lok_val, data_val, wagon_val.strip()]]
                    )
                    st.success(f"✅ Dodano wpis LP={lp}: **{wagon_val}**")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Błąd arkusza: {e}")

        with st.expander("🔍 Surowy tekst z Google Vision (do diagnostyki)"):
            st.text(dane["ocr_tekst"])
