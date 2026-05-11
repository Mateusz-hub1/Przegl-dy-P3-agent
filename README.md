

#  SPK KORCZ — Skaner i Rejestr DDU / Przegląd P3

Inteligentne narzędzie webowe do automatyzacji cyfryzacji protokołów dopuszczenia do użytkowania (DDU) oraz przeglądów taboru kolejowego poziomu P3. Aplikacja rozpoznaje pismo drukowane i odręczne, wyodrębnia kluczowe dane techniczne i kataloguje je w chmurowym arkuszu Google Sheets .

**🔗 Adres aplikacji:** [https://przeglady-p3-agent-spk.streamlit.app/](https://www.google.com/search?q=https://przeglady-p3-agent-spk.streamlit.app/)

---

##  Główne Funkcje

* **Masowe przetwarzanie PDF:** Możliwość wgrania wielu plików jednocześnie. System kolejkuję zadania i przetwarza je automatycznie jeden po drugim.
* 
**Inteligentna lokalizacja strony DDU:** Program przeszukuje wielostronicowe dokumenty P3 (często liczące ponad 100 stron), aby odnaleźć właściwy "Protokół P6 / Dopuszczenie do użytkowania" .


* **Wzmocniony Silnik OCR (Tesseract):** Wykorzystuje darmowy silnik Tesseract z autorskim modułem poprawy kontrastu i odszumiania obrazu, co znacząco poprawia odczyt pisma odręcznego na skanach.
* **Ekstrakcja Danych:** Automatyczne rozpoznawanie:
* **Numeru Wagonu** (12 cyfr w formacie UIC).
* **Numeru Dopuszczenia** (pismo odręczne).
* **Daty wystawienia** (z pominięciem daty szablonu dokumentu).
* **Lokalizacji / Zakładu** (np. KWK Piast).


* **Panel Weryfikacji:** Interfejs "Side-by-Side" pozwalający użytkownikowi porównać obraz dokumentu z odczytanymi danymi i wprowadzić ewentualne poprawki przed zapisem.
* **Integracja z Google Sheets:** Automatyczne dopisywanie rekordów do rejestru z zachowaniem ciągłości numeracji porządkowej (LP).

---

##  Stos Technologiczny

* **Framework:** Streamlit (Interfejs Webowy)
* **Przetwarzanie PDF:** PyMuPDF (fitz)
* **OCR:** Tesseract OCR (pozycjonowanie lokalne)
* **Przetwarzanie obrazu:** Pillow (PIL)
* **Baza danych:** Google Sheets API (gspread)
* **Stylizacja:** Custom CSS (KORCZ Industrial Brand)

---

##  Wymagania i Instalacja (Lokalnie)

Aby uruchomić projekt lokalnie, należy zainstalować silnik Tesseract OCR oraz biblioteki Pythona:

1. **Silnik OCR:**
* macOS: `brew install tesseract tesseract-lang`
* Windows: Pobierz i zainstaluj instalator ze strony UB-Mannheim.


2. **Biblioteki Python:**
```bash
pip install streamlit PyMuPDF pytesseract Pillow gspread google-auth

```


3. **Pliki konfiguracyjne:**
* 
`packages.txt`: Musi zawierać `tesseract-ocr` i `tesseract-ocr-pol`.


* 
`requirements.txt`: Lista bibliotek wymienionych wyżej.





---

##  Konfiguracja API i Bezpieczeństwo

Aplikacja korzysta z **Google Service Account** do komunikacji z Arkuszami Google.

* 
**Klucze:** Zawartość pliku JSON konta usługi (`przeglad-p3-71731e37fbe8.json`) musi zostać wklejona do panelu Streamlit w sekcji `Secrets` pod kluczem `[gcp_service_account]`.


* 
**Uprawnienia:** Adres e-mail bota (`agent-arkusze-p3@przeglad-p3.iam.gserviceaccount.com`) musi posiadać uprawnienia **Edytora** w docelowym arkuszu Google Sheets.



---

##  Instrukcja Obsługi

1. Wgraj pliki PDF za pomocą wrzutni na górze strony.
2. System wyświetli listę przetworzonych plików wraz ze statusem (OK / Korekta).
3. Kliknij ikonę edycji **✏️**, aby otworzyć panel podglądu dokumentu.
4. Sprawdź poprawność danych, popraw ewentualne błędy odczytu.
5. Kliknij **Wyślij**, aby dodać pojedynczy wpis, lub użyj przycisku zbiorczego **🚀 WYŚLIJ WSZYSTKIE GOTOWE**, aby zarchiwizować całą paczkę dokumentów naraz.

---

