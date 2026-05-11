import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Skaner Przeglądów P3", layout="centered")
st.title("📄 Skaner Przeglądów P3 do Arkusza")
st.markdown("Wgraj skan formularza P3 w formacie PDF, a system automatycznie odczyta dane i wyśle je do Google Sheets.")


# --- POŁĄCZENIE Z GOOGLE SHEETS ---
@st.cache_resource
def get_google_client():
    # Pobieranie kluczy ukrytych w "Sekretach" Streamlita
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    return gspread.authorize(creds)


# Podaj dokładną nazwę swojego arkusza:
ARKUSZ_NAZWA = "Rejestr_P3"


# --- LOGIKA ROZPOZNAWANIA TEKSTU ---
def analizuj_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""

    # Pasek postępu dla użytkownika
    progress_bar = st.progress(0)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes()))
        text = pytesseract.image_to_string(img, lang='pol')
        full_text += text + "\n"
        progress_bar.progress((i + 1) / len(doc))

    doc.close()

    # Ekstrakcja danych (wyrażenia regularne)
    wagon_match = re.search(r'(\d{2})\s*(\d{2})\s*(\d{4})\s*(\d{3})\s*-\s*(\d)', full_text)
    wagon_number = f"{wagon_match.group(1)}{wagon_match.group(2)} {wagon_match.group(3)} {wagon_match.group(4)}-{wagon_match.group(5)}" if wagon_match else "Brak"

    date_match = re.search(r'\d{2}\.\d{2}\.\d{2,4}', full_text)
    date = date_match.group(0) if date_match else "Brak"

    dop_match = re.search(r'DOPUSZCZENIE[\s\S]{0,100}?Nr\.?\s*([\d\s]{7,15})', full_text, re.IGNORECASE)
    numer_dopuszczenia = dop_match.group(1).strip() if dop_match else "Brak"

    location = "KWK Piast" if "KWK Piast" in full_text else "Brak"

    return date, wagon_number, numer_dopuszczenia, location


# --- INTERFEJS UŻYTKOWNIKA ---
uploaded_file = st.file_uploader("Wybierz plik PDF", type="pdf")

if uploaded_file is not None:
    if st.button("Rozpocznij skanowanie"):
        with st.spinner("Analizowanie dokumentu (to może chwilę potrwać)..."):
            # 1. Wyciąganie danych
            data, wagon, nr_dop, miejscowosc = analizuj_pdf(uploaded_file.read())

            # 2. Wyświetlenie wyników
            st.success("Analiza zakończona!")
            st.write(f"**Data:** {data}")
            st.write(f"**Nr Wagonu:** {wagon}")
            st.write(f"**Nr Dopuszczenia:** {nr_dop}")
            st.write(f"**Miejscowość:** {miejscowosc}")

            # 3. Wysyłanie do arkusza
            try:
                client = get_google_client()
                sheet = client.open(ARKUSZ_NAZWA).sheet1

                wartosci_lp = sheet.col_values(1)
                lp = 1 if len(wartosci_lp) <= 1 else int(wartosci_lp[-1]) + 1 if wartosci_lp[-1].isdigit() else len(
                    wartosci_lp)

                nowy_wiersz = [lp, nr_dop, miejscowosc, data, wagon]
                sheet.append_row(nowy_wiersz)
                st.balloons()
                st.success(f"Dane pomyślnie dodane do arkusza jako pozycja LP: {lp}!")
            except Exception as e:
                st.error(f"Wystąpił błąd podczas łączności z Arkuszem: {e}")
                st.info("Upewnij się, że udostępniłeś arkusz adresowi e-mail z Google Cloud!")