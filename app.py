import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import io
import re
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# KONFIGURACJA STRONY
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Skaner DDU / P3", layout="wide")
st.title("📋 Skaner Dopuszczeń — DDU / Przegląd P3")
st.markdown(
    "Wgraj DDU (1 strona) lub pełny Przegląd P3 (wielostronicowy). "
    "Program znajdzie stronę dopuszczenia, pokaże jej obraz i wypełni pola — "
    "sprawdź dane i wyślij do rejestru."
)

# ---------------------------------------------------------------------------
# POŁĄCZENIE Z GOOGLE SHEETS
# !!! WKLEJ TUTAJ LINK DO SWOJEGO ARKUSZA !!!
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
# FUNKCJE POMOCNICZE — EKSTRAKCJA DANYCH
# ===========================================================================

def formatuj_wagon(cyfry_12: str) -> str:
    """12 cyfr → 'XXXX XXXX XXX-X'"""
    d = cyfry_12
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}"


def wagon_z_nazwy_pliku(filename: str) -> str:
    """
    Najniezawodniejsza metoda — wyciąga numer wagonu z nazwy pliku.
    Działa dla plików nazwanych jak: Przegląd_P3_33516666408-6.pdf
    Szukamy ciągu 12 cyfr (opcjonalne separatory: spacja, podkreślnik, myślnik).
    """
    # Normalizujemy: zostawiamy tylko cyfry i myślniki do analizy
    # Wzorzec: 4 cyfry + separator? + 4 cyfry + separator? + 3 cyfry + separator? + 1 cyfra
    m = re.search(r"(\d{4})[\s_\-]?(\d{4})[\s_\-]?(\d{3})[\s_\-](\d)", filename)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)
    return ""


def wagon_z_ocr(text: str) -> str:
    """
    Próbuje wyciągnąć numer wagonu z tekstu OCR.
    Strategia A: szukaj wzorca XXXX XXXX XXX-X w tekście.
    Strategia B: szukaj cyfr przy słowie 'wagonu'.
    """
    # Strategia A: klasyczny format z spacjami lub separatorami
    m = re.search(r"(\d{4})[\s\.,]{1,4}(\d{4})[\s\.,]{1,4}(\d{3})[\s\-](\d)", text)
    if m:
        all_digits = "".join(m.groups())
        if len(all_digits) == 12:
            return formatuj_wagon(all_digits)

    # Strategia B: szukaj cyfr w pobliżu słowa 'wagonu' / 'wagon'
    m2 = re.search(
        r"wagon[ou][\s\.\:\-]{0,30}([\d\s,\.\-]{10,30})", text, re.IGNORECASE
    )
    if m2:
        cyfry = re.findall(r"\d", m2.group(1))
        if len(cyfry) >= 12:
            return formatuj_wagon("".join(cyfry[:12]))

    return ""


def nr_dop_z_ocr(text: str) -> str:
    """
    Szuka numeru dopuszczenia przy słowie 'Nr' w kontekście DDU.
    Np. 'Nr. 1704 4086' → '17044086'
    """
    m = re.search(r"\bNr[\.\s:]{1,5}([\d\s]{5,14})", text, re.IGNORECASE)
    if m:
        val = re.sub(r"\s", "", m.group(1)).strip()
        # Musi mieć min. 6 cyfr i nie być numerem NIP/REGON (9+ cyfr)
        if 6 <= len(val) <= 12:
            return val
    return ""


def data_z_ocr(text: str) -> str:
    """
    Szuka daty wystawienia DDU — pomija datę szablonu z nagłówka (04.05.2020).
    Obsługuje formaty DD.MM.RR i DD.MM.RRRR z opcjonalnym przyrostkiem r/n.
    """
    NAGLOWEK_TEMPLATE = r"04[\.\-]05[\.\-]2020"

    for m in re.finditer(
        r"(\d{1,2})[\.\-](\d{2})[\.\-](\d{2,4})[rRnN\.]?", text
    ):
        pelna = m.group(0)
        if re.search(NAGLOWEK_TEMPLATE, pelna):
            continue  # pomiń datę szablonu

        dzien, miesiac, rok = m.group(1), m.group(2), m.group(3)
        if len(rok) == 2:
            rok = "20" + rok

        # Prosta walidacja zakresu
        if 1 <= int(dzien) <= 31 and 1 <= int(miesiac) <= 12:
            return f"{dzien.zfill(2)}.{miesiac}.{rok}"

    return ""


def lokalizacja_z_ocr(text: str) -> str:
    """
    Szuka lokalizacji w linii z 'KWK' (kopalnie) lub innych nazw własnych
    przed datą wystawienia — kontekst '(miejsce i data wystawienia)'.

    Uwaga: OCR często myli litery w nazwie (np. Piast → Rast), ale 'KWK'
    jako duże drukowane litery jest zazwyczaj rozpoznawane poprawnie.
    """
    # Preferowana ścieżka: KWK + nazwa (duże litery drukowane)
    m = re.search(r"KWK\s+([A-ZŁÓŚĄĆĘŹŻa-ząćęłńóśźż]{2,}(?:\s+[A-Za-ząćęłńóśźż]+)?)", text)
    if m:
        return ("KWK " + m.group(1).strip()).title().replace("Kwk", "KWK")

    # Fallback: tekst przed datą na tej samej linii (np. "Zakład X 17.04.2026")
    m2 = re.search(
        r"([A-ZŁÓŚĄĆĘŹŻ][A-Za-ząćęłńóśźżŁÓŚĄĆĘŹŻ ]{3,30})\s+\d{1,2}[\.\-]\d{2}[\.\-]\d{2}",
        text,
    )
    if m2:
        kandydat = m2.group(1).strip()
        # Odrzuć fałszywe trafienia (nazwy z formularza)
        SZUM = {"Serwis", "Marcin", "Sylwester", "Kercz", "Inter", "Komtrans"}
        if not any(s in kandydat for s in SZUM):
            return kandydat

    return ""


# ===========================================================================
# FUNKCJE OBSŁUGI PDF
# ===========================================================================

def ocr_strony(page, dpi: int = 300) -> str:
    """OCR jednej strony z wzmocnieniem kontrastu (pomaga przy skanach)."""
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes())).convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    return pytesseract.image_to_string(img, lang="pol", config="--psm 6 --oem 1")


def znajdz_strone_ddu(doc) -> int:
    """
    Wyszukuje stronę DDU (Protokół P6 / Dopuszczenie do użytkowania).
    Skanuje od końca dokumentu — DDU jest zazwyczaj ostatnią stroną.
    Dla 1-stronicowych plików zawsze zwraca 0.
    """
    if len(doc) == 1:
        return 0

    # Szybki scan na 100 DPI od końca (max 8 ostatnich stron)
    for i in range(len(doc) - 1, max(len(doc) - 9, -1), -1):
        pix = doc[i].get_pixmap(dpi=100)
        img = Image.open(io.BytesIO(pix.tobytes()))
        tekst_quick = pytesseract.image_to_string(img, lang="pol")
        upper = tekst_quick.upper()
        if "DOPUSZCZENIE" in upper or ("PROTOKÓŁ" in upper and "P6" in upper):
            return i

    # Fallback: ostatnia strona
    return len(doc) - 1


def renderuj_podglad(page, dpi: int = 150) -> bytes:
    """Zwraca bytes PNG strony — do wyświetlenia w Streamlit."""
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")


# ===========================================================================
# GŁÓWNA LOGIKA PRZETWARZANIA
# ===========================================================================

def przetworz_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """
    Otwiera PDF, lokalizuje stronę DDU, robi OCR i zwraca słownik z danymi.
    Zwraca też bytes podglądu i surowy tekst OCR do weryfikacji.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_stron = len(doc)

    # 1. Znajdź stronę DDU
    with st.spinner(f"Szukam strony DDU w {n_stron}-stronicowym pliku..."):
        ddu_idx = znajdz_strone_ddu(doc)

    # 2. Podgląd obrazu (szybki, niskie DPI)
    podglad_bytes = renderuj_podglad(doc[ddu_idx], dpi=150)

    # 3. OCR na pełnym DPI
    with st.spinner("Wykonuję OCR strony DDU (może chwilę potrwać)..."):
        ddu_text = ocr_strony(doc[ddu_idx], dpi=300)

    doc.close()

    # 4. Ekstrakcja danych — wagon z nazwy pliku jest najniezawodniejszy
    wagon = wagon_z_nazwy_pliku(filename) or wagon_z_ocr(ddu_text)
    nr_dop = nr_dop_z_ocr(ddu_text)
    data = data_z_ocr(ddu_text)
    lokalizacja = lokalizacja_z_ocr(ddu_text)

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

    # --- Układ dwukolumnowy: obraz DDU | formularz ---
    col_img, col_form = st.columns([1, 1], gap="large")

    with col_img:
        st.subheader("📄 Strona dopuszczenia (DDU)")
        st.caption(
            f"Plik: **{uploaded_file.name}** | "
            f"Znaleziona strona DDU: **{dane['ddu_strona']}/{dane['n_stron']}**"
        )
        st.image(dane["podglad_png"], use_container_width=True)

    with col_form:
        st.subheader("✏️ Dane do rejestru")
        st.markdown(
            "_Sprawdź dane na obrazie obok i popraw jeśli OCR się pomylił._"
        )

        # Wskaźniki statusu
        def status_icon(val: str) -> str:
            return "✅" if val else "⚠️"

        st.caption(
            f"{status_icon(dane['wagon'])} Wagon  "
            f"{status_icon(dane['nr_dop'])} Nr dopuszczenia  "
            f"{status_icon(dane['data'])} Data  "
            f"{status_icon(dane['lokalizacja'])} Lokalizacja"
        )

        wagon_val = st.text_input(
            "🚂 Numer wagonu *",
            value=dane["wagon"],
            placeholder="np. 3351 6666 408-6",
            help="12-cyfrowy numer w formacie XXXX XXXX XXX-X — wymagany!",
        )
        nr_dop_val = st.text_input(
            "📑 Numer dopuszczenia",
            value=dane["nr_dop"],
            placeholder="np. 17044086",
            help="Numer z pola 'Nr.' na dokumencie DDU",
        )
        data_val = st.text_input(
            "📅 Data wystawienia",
            value=dane["data"],
            placeholder="np. 17.04.2026",
            help="Format DD.MM.RRRR",
        )
        lok_val = st.text_input(
            "📍 Miejscowość / Zakład",
            value=dane["lokalizacja"],
            placeholder="np. KWK Piast",
            help="Lokalizacja z pola '(miejsce i data wystawienia)'",
        )

        st.divider()

        wyslij = st.button(
            "✅ Wyślij do rejestru Google Sheets",
            type="primary",
            use_container_width=True,
        )

        if wyslij:
            if not wagon_val.strip():
                st.error("❌ Numer wagonu jest wymagany — sprawdź obrazek i wpisz ręcznie.")
            else:
                try:
                    client = get_google_client()
                    sheet = client.open_by_url(ARKUSZ_URL).sheet1

                    # Wyznacz kolejny numer LP
                    wszystkie_lp = sheet.col_values(1)
                    lp = 1 if len(wszystkie_lp) <= 1 else int(wszystkie_lp[-1]) + 1

                    sheet.append_rows(
                        [[lp, nr_dop_val, lok_val, data_val, wagon_val.strip()]]
                    )
                    st.success(f"✅ Dodano wpis LP={lp}: **{wagon_val}**")
                    st.balloons()

                except Exception as e:
                    st.error(f"❌ Błąd połączenia z Arkuszem: {e}")

        # Podgląd OCR do debugowania
        with st.expander("🔍 Surowy tekst OCR (do diagnostyki)"):
            st.text(dane["ocr_tekst"])
