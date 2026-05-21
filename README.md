<div align="center">

<br/>

# 🚂 KORCZ — Skaner Dokumentów Kolejowych

**Automatyczne skanowanie, OCR i archiwizacja dokumentów DDU / P3 / Mw 581**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Tesseract](https://img.shields.io/badge/Tesseract_OCR-5.x-339933?style=flat-square)](https://github.com/tesseract-ocr/tesseract)
[![Google Sheets](https://img.shields.io/badge/Google_Sheets-API_v4-34A853?style=flat-square&logo=google-sheets&logoColor=white)](https://developers.google.com/sheets)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

<br/>

*Tryb ciemny (aurora) · Tryb jasny dostępny jednym kliknięciem*

<br/>

</div>

---

## Czym jest KORCZ?

KORCZ to wewnętrzna aplikacja webowa dla **SPK Korcz Serwis Pojazdów Kolejowych**, która automatyzuje rejestrację dokumentacji przeglądowej wagonów towarowych. Zamiast ręcznego przepisywania danych z papierowych protokołów, wystarczy wrzucić skan — system sam odczyta numer wagonu, datę, lokalizację i typ dokumentu, a następnie wyśle wpis do odpowiedniego arkusza Google Sheets.

### Co robi

- 📄 **Wczytuje** PDF, JPG i PNG — pojedynczo lub zbiorczo
- 🔍 **Rozpoznaje tekst** przez OCR (Tesseract + PyMuPDF) z preprocessing obrazu
- 🧠 **Klasyfikuje dokumenty** automatycznie: P3 (Przegląd P3 / Protokół P6) lub DDU (Mw 581 / P1·P2)
- 📑 **Wybiera właściwą stronę** w wielostronicowych PDF-ach — algorytm punktowy skanuje każdą stronę i wybiera tę najbardziej dopasowaną do formularza P6, unikając pomyłek z P1/P2
- 🚃 **Wyciąga numery wagonów** — jeden (P3) lub wiele z tabeli (DDU)
- 📊 **Zapisuje do Google Sheets** — osobne arkusze dla P3 i DDU
- ✏️ **Umożliwia korektę** każdego wpisu z podglądem dokumentu i surowym tekstem OCR
- 🌓 **Obsługuje tryb ciemny i jasny**

---

## Stos technologiczny

| Warstwa | Technologia |
|---|---|
| Frontend / UI | [Streamlit](https://streamlit.io) + własny CSS (aurora glassmorphism) |
| OCR | [Tesseract 5](https://github.com/tesseract-ocr/tesseract) via `pytesseract` |
| PDF → obraz | [PyMuPDF (`fitz`)](https://pymupdf.readthedocs.io) |
| Preprocessing obrazu | [Pillow](https://pillow.readthedocs.io) — skala szarości, kontrast, ostrość |
| Google Sheets | [`gspread`](https://docs.gspread.org) + [Google OAuth2](https://google-auth.readthedocs.io) |
| Język | Python 3.10+ |

---

## Wymagania

### System

- Python **3.10** lub nowszy
- **Tesseract OCR 5.x** z paczką języka polskiego

```bash
# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-pol

# macOS (Homebrew)
brew install tesseract
brew install tesseract-lang   # zawiera pol.traineddata

# Windows
# Pobierz instalator z: https://github.com/UB-Mannheim/tesseract/wiki
# Dodaj ścieżkę do PATH, np: C:\Program Files\Tesseract-OCR
```

### Python

Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

<details>
<summary><code>requirements.txt</code></summary>

```
streamlit>=1.35.0
pymupdf>=1.24.0
pytesseract>=0.3.10
Pillow>=10.0.0
gspread>=6.0.0
google-auth>=2.20.0
```

</details>

---

## Struktura projektu

```
korcz-skaner/
├── app.py                   # Główna aplikacja
├── requirements.txt
├── logo_spkkorcz.png        # Logo (opcjonalne, nie w repo)
├── .streamlit/
│   └── secrets.toml         # Sekrety lokalne (nie w repo)
├── .gitignore
├── LICENSE
└── README.md
```

---

## Jak działa klasyfikacja stron PDF

Wielostronicowe dokumenty DDU zawierają często zarówno strony P6 (Dopuszczenie do użytkowania), jak i P1/P2 (naprawa). Starsze podejście — skanowanie od końca z `break` na pierwszym trafieniu — powodowało błędy.

Obecny algorytm (`_znajdz_strone_p6`) ocenia **każdą stronę** dokumentu osobno:

| Słowo kluczowe na stronie | Punkty |
|---|---|
| `DOPUSZCZENIE DO UŻYTKOWANIA` | +30 |
| `PROTOKÓŁ P6` / `PROTOKOL P6` | +25 |
| `PRZEGLĄD P3` / `PRZEGLAD P3` | +20 |
| ` P6 ` (samodzielne) | +10 |
| `WAGONU TOWAROWEGO` | +8 |
| `DOPUSZCZENIE` (ogólne) | +6 |
| `ZAWIADOMIENIE O NAPRAWIE` | −20 |
| `PROTOKÓŁ ODBIORU` | −15 |
| `MW 581` | −15 |
| `SPIS WAGONÓW` | −10 |
| `NAPRAWA POZIOMU P` | −8 |
| ` P2 ` (samodzielne) | −5 |

Wybierana jest strona z **najwyższym łącznym wynikiem**. Detekcja działa na 150 DPI (dobry balans jakości i szybkości), właściwy OCR na 300 DPI.

---

## Tryby skanowania

| Tryb | Zachowanie |
|---|---|
| **AUTO** | Aplikacja sama wykrywa typ dokumentu na podstawie treści OCR |
| **P3** | Wymuszony tryb P3 — jeden wagon na plik, zapis do arkusza P3 |
| **DDU** | Wymuszony tryb DDU — wyciąga wszystkie wagony z tabeli, zapis do arkusza DDU |

---

## Znane ograniczenia

- OCR działa najlepiej na skanach w rozdzielczości ≥ 200 DPI; zdjęcia robione telefonem z dużym kątem mogą dawać gorsze wyniki
- Wykrywanie lokalizacji oparte jest na liście znanych zakładów — nowe lokalizacje warto dopisać do listy `ZNANE` w `app.py`
- Numery telefonów zaczynające się od `48`, `881`, `882`, `535`, `538` są odfiltrowywane jako potencjalne fałszywe numery wagonów; prefiks filtra można rozszerzyć w `_znajdz_wagony_raw`

---

## Licencja

[MIT](LICENSE) © SPK Korcz Serwis Pojazdów Kolejowych

---

<div align="center">
<sub>Zbudowane z ♥ dla kolejarzy. Pytania i zgłoszenia błędów przez <a href="../../issues">Issues</a>.</sub>
</div>
