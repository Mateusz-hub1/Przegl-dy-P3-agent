import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Skaner Przeglądów P3", layout="wide")
st.title("📄 Masowy Skaner Dopuszczeń P3")
st.markdown("Wgraj plik PDF zawierający **wiele dopuszczeń** (np. skan 6 kartek na raz). Program odczyta każdą stronę osobno i dopisze je jako kolejne wiersze do Google Sheets.")

# --- POŁĄCZENIE Z GOOGLE SHEETS ---
@st.cache_resource
def get_google_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    return gspread.authorize(creds)

# TUTAJ WKLEJ SWÓJ LINK DO ARKUSZA (Zostaw w cudzysłowach!)
ARKUSZ_URL = "https://docs.google.com/spreadsheets/d/1Np2uu4NI7cJ2vYeNuC57ugAQ0wKsvN5gPqUqY745Ikw/edit?usp=sharing" 

# --- LOGIKA ROZPOZNAWANIA TEKSTU ---
def analizuj_wielokrotny_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    wszystkie_dane = []
    
    progress_bar = st.progress(0)
    
    # Przechodzimy przez PDF STRONA PO STRONIE
    for i, page in enumerate(doc):
        page_text = page.get_text()
        
        # Jeśli strona to płaski skan, używamy OCR
        if len(page_text.strip()) < 50:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            page_text = pytesseract.image_to_string(img, lang='pol')
            
        # Ekstrakcja tylko dla DANEJ STRONY
        wagon_match = re.search(r'(\d{2})[\s\-]*(\d{2})[\s\-]*(\d{4})[\s\-]*(\d{3})[\s\-]*(\d)', page_text)
        wagon_number = f"{wagon_match.group(1)}{wagon_match.group(2)} {wagon_match.group(3)} {wagon_match.group(4)}-{wagon_match.group(5)}" if wagon_match else "Brak"

        dop_match = re.search(r'Nr\.?[\s\_]*([\d\s]{7,15})', page_text)
        numer_dopuszczenia = dop_match.group(1).strip() if dop_match else "Brak"

        date_match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})', page_text)
        if date_match:
            date = date_match.group(1)
            if date.endswith('.'): date = date[:-1]
        else:
            date = "Brak"

        location = "KWK Piast" if re.search(r'KWK\s*Piast', page_text, re.IGNORECASE) else "Brak (lub inna)"

        # Jeśli na stronie jest wagon LUB numer dopuszczenia, uznajemy to za dokument i dodajemy do listy
        if wagon_number != "Brak" or numer_dopuszczenia != "Brak":
            wszystkie_dane.append({
                "strona": i + 1,
                "data": date, 
                "wagon": wagon_number, 
                "nr_dop": numer_dopuszczenia, 
                "miejscowosc": location
            })
            
        progress_bar.progress((i + 1) / len(doc))
        
    doc.close()
    return wszystkie_dane

# --- INTERFEJS UŻYTKOWNIKA ---
uploaded_file = st.file_uploader("Wybierz plik PDF (Wiele Dopuszczeń)", type="pdf")

if uploaded_file is not None:
    if st.button("Rozpocznij skanowanie paczki"):
        with st.spinner("Analizowanie dokumentów strona po stronie..."):
            wykryte_dokumenty = analizuj_wielokrotny_pdf(uploaded_file.read())
            
            if not wykryte_dokumenty:
                st.warning("Nie znaleziono żadnych danych na żadnej ze stron. Sprawdź plik PDF.")
            else:
                st.success(f"Znaleziono {len(wykryte_dokumenty)} poprawnie wypełnionych dopuszczeń! Przesyłanie do Arkusza...")
                
                # Wyświetlamy tabelkę z podsumowaniem dla użytkownika
                st.write("Podgląd odczytanych danych:")
                st.table(wykryte_dokumenty)
                
                try:
                    client = get_google_client()
                    sheet = client.open_by_url(ARKUSZ_URL).sheet1
                    
                    # Sprawdzamy numerację (LP)
                    wartosci_lp = sheet.col_values(1)
                    if len(wartosci_lp) <= 1:
                        start_lp = 1
                    else:
                        try:
                            start_lp = int(wartosci_lp[-1]) + 1
                        except ValueError:
                            start_lp = len(wartosci_lp)
                    
                    # Przygotowujemy listę wierszy do wysłania hurtowo
                    nowe_wiersze = []
                    for dok in wykryte_dokumenty:
                        nowy_wiersz = [start_lp, dok["nr_dop"], dok["miejscowosc"], dok["data"], dok["wagon"]]
                        nowe_wiersze.append(nowy_wiersz)
                        start_lp += 1
                        
                    # Wysyłamy wszystko na raz
                    sheet.append_rows(nowe_wiersze)
                    
                    st.balloons()
                    st.success(f"Sukces! Wszystkie {len(nowe_wiersze)} wierszy zostało dodanych do arkusza Google!")
                except Exception as e:
                    st.error(f"Wystąpił błąd podczas łączności z Arkuszem: {e}")
