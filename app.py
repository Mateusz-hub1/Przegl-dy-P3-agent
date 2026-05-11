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
st.title("📄 Elastyczny Skaner Dopuszczeń P3")
st.markdown("Program automatycznie wykrywa dane na stronach PDF i dopisuje je do rejestru.")

# --- POŁĄCZENIE Z GOOGLE SHEETS ---
@st.cache_resource
def get_google_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    return gspread.authorize(creds)

# !!! TUTAJ WKLEJ LINK DO SWOJEGO ARKUSZA GOOGLE !!!
ARKUSZ_URL = "TWÓJ_LINK_DO_ARKUSZA_GOOGLE" 

def wyciagnij_cyfry(text):
    """Usuwa wszystko poza cyframi z tekstu."""
    return "".join(re.findall(r'\d', text))

def analizuj_strone(text):
    """Bardzo elastyczna ekstrakcja danych z tekstu strony."""
    # 1. WAGON (Szukamy 12 cyfr w całym tekście strony)
    # Wyciągamy wszystkie ciągi cyfr i sprawdzamy, czy któryś ma 12 znaków
    cyfry_tekst = wyciagnij_cyfry(text)
    wagon = "Brak"
    # Szukamy ciągu 12 cyfr w tekście (często występują obok siebie)
    wagon_match = re.search(r'\d{12}', cyfry_tekst)
    if wagon_match:
        w = wagon_match.group(0)
        wagon = f"{w[0:4]} {w[4:8]} {w[8:11]}-{w[11]}"
    else:
        # Próba znalezienia 12 cyfr rozrzuconych (np. ze spacjami)
        potential = re.findall(r'\d', text)
        if len(potential) >= 12:
            # Bierzemy pierwsze 12 cyfr jako numer wagonu
            w = "".join(potential[:12])
            wagon = f"{w[0:4]} {w[4:8]} {w[8:11]}-{w[11]}"

    # 2. NR DOPUSZCZENIA (Szukamy numeru po słowie 'Nr' lub 'DOPUSZCZENIE')
    nr_dop = "Brak"
    dop_match = re.search(r'(?:Nr|Dopuszczenie)[\.\s\:]*([\d\s]{4,12})', text, re.IGNORECASE)
    if dop_match:
        nr_dop = dop_match.group(1).strip().replace(" ", "")

    # 3. DATA (Standardowy format DD.MM.RR/RRRR)
    date_match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})', text)
    date = date_match.group(1).rstrip('.') if date_match else "Brak"

    # 4. MIEJSCOWOŚĆ
    location = "KWK Piast" if re.search(r'KWK\s*Piast', text, re.IGNORECASE) else "Brak"
    
    return {"data": date, "wagon": wagon, "nr_dop": nr_dop, "miejscowosc": location}

def procesuj_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    wyniki = []
    pb = st.progress(0)
    
    for i, page in enumerate(doc):
        page_text = page.get_text()
        # Jeśli strona jest skanem (mało tekstu), wymuś OCR [cite: 494-542]
        if len(page_text.strip()) < 40:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            page_text = pytesseract.image_to_string(img, lang='pol')
        
        dane = analizuj_strone(page_text)
        # Dodajemy stronę do wyników, jeśli znaleziono wagon LUB numer dopuszczenia
        if dane["wagon"] != "Brak" or dane["nr_dop"] != "Brak":
            wyniki.append(dane)
        
        pb.progress((i + 1) / len(doc))
    
    doc.close()
    return wyniki

# --- INTERFEJS ---
uploaded_file = st.file_uploader("Wgraj dowolny PDF z dopuszczeniami", type="pdf")

if uploaded_file and st.button("Skanuj i wyślij do rejestru"):
    with st.spinner("Analizowanie dokumentów..."):
        paczka_danych = procesuj_pdf(uploaded_file.read())
        
        if not paczka_danych:
            st.error("Nie znaleziono danych na żadnej ze stron. Spróbuj wyraźniejszego skanu.")
        else:
            st.write(f"Odczytano {len(paczka_danych)} rekord(y):")
            st.table(paczka_danych)
            
            try:
                client = get_google_client()
                sheet = client.open_by_url(ARKUSZ_URL).sheet1
                
                # Dynamiczne ustalanie LP (ostatni wiersz w kolumnie A)
                wszystkie_lp = sheet.col_values(1)
                lp = 1 if len(wszystkie_lp) <= 1 else int(wszystkie_lp[-1]) + 1
                
                wiersze_do_zapisu = []
                for d in paczka_danych:
                    wiersze_do_zapisu.append([lp, d["nr_dop"], d["miejscowosc"], d["data"], d["wagon"]])
                    lp += 1
                
                sheet.append_rows(wiersze_do_zapisu)
                st.success(f"Pomyślnie dodano {len(wiersze_do_zapisu)} wpisów!")
                st.balloons()
            except Exception as e:
                st.error(f"Błąd połączenia z Arkuszem: {e}")
