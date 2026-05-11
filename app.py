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
st.markdown("Wgraj plik PDF z wieloma dopuszczeniami. Dane zostaną dopisane do rejestru od drugiego wiersza.")

# --- POŁĄCZENIE Z GOOGLE SHEETS ---
@st.cache_resource
def get_google_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    return gspread.authorize(creds)

# !!! TUTAJ WKLEJ LINK DO SWOJEGO ARKUSZA GOOGLE !!!
ARKUSZ_URL = "TWÓJ_LINK_DO_ARKUSZA_GOOGLE" 

def analizuj_strone(text):
    """Wyciąga dane z tekstu jednej strony dokumentu."""
    # Nr wagonu: szuka 12 cyfr ignorując niemal wszystko pomiędzy nimi [cite: 502]
    wagon_match = re.search(r'(\d{2})[\s\.\-]*(\d{2})[\s\.\-]*(\d{4})[\s\.\-]*(\d{3})[\s\.\-]*(\d)', text)
    wagon = f"{wagon_match.group(1)}{wagon_match.group(2)} {wagon_match.group(3)} {wagon_match.group(4)}-{wagon_match.group(5)}" if wagon_match else "Brak"

    # Nr dopuszczenia: szuka po słowie 'Nr' [cite: 501]
    dop_match = re.search(r'Nr[\.\s\_]*([\d\s]{4,15})', text, re.IGNORECASE)
    nr_dop = dop_match.group(1).strip().replace(" ", "") if dop_match else "Brak"

    # Data: format DD.MM.RR lub DD.MM.RRRR [cite: 503]
    date_match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})', text)
    date = date_match.group(1).rstrip('.') if date_match else "Brak"

    # Miejscowość: szuka KWK Piast [cite: 503]
    location = "KWK Piast" if re.search(r'KWK\s*Piast', text, re.IGNORECASE) else "Brak"
    
    return {"data": date, "wagon": wagon, "nr_dop": nr_dop, "miejscowosc": location}

def procesuj_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    wyniki = []
    pb = st.progress(0)
    
    for i, page in enumerate(doc):
        # Wyciągamy tekst (cyfrowy lub OCR jeśli skan) [cite: 487-542]
        page_text = page.get_text()
        if len(page_text.strip()) < 30:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            page_text = pytesseract.image_to_string(img, lang='pol')
        
        dane = analizuj_strone(page_text)
        # Dodajemy tylko jeśli coś sensownego znaleziono na stronie 
        if dane["wagon"] != "Brak" or dane["nr_dop"] != "Brak":
            wyniki.append(dane)
        
        pb.progress((i + 1) / len(doc))
    
    doc.close()
    return wyniki

# --- INTERFEJS ---
uploaded_file = st.file_uploader("Wgraj PDF (jedno lub wiele dopuszczeń)", type="pdf")

if uploaded_file and st.button("Skanuj i wyślij"):
    with st.spinner("Pracuję..."):
        paczka_danych = procesuj_pdf(uploaded_file.read())
        
        if not paczka_danych:
            st.error("Nie znaleziono danych. Upewnij się, że plik to 'Dopuszczenie do użytkowania'.")
        else:
            st.write(f"Znaleziono {len(paczka_danych)} dokumentów:")
            st.table(paczka_danych)
            
            try:
                client = get_google_client()
                sheet = client.open_by_url(ARKUSZ_URL).sheet1
                
                # Ustalanie kolejnego numeru LP (od drugiego wiersza)
                wszystkie_lp = sheet.col_values(1)
                lp = 1 if len(wszystkie_lp) <= 1 else int(wszystkie_lp[-1]) + 1
                
                wiersze_do_zapisu = []
                for d in paczka_danych:
                    wiersze_do_zapisu.append([lp, d["nr_dop"], d["miejscowosc"], d["data"], d["wagon"]])
                    lp += 1
                
                sheet.append_rows(wiersze_do_zapisu)
                st.success(f"Dodano {len(wiersze_do_zapisu)} wpisów do rejestru!")
                st.balloons()
            except Exception as e:
                st.error(f"Błąd arkusza: {e}")
