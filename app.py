import io
import re
import numpy as np
from PIL import Image

# ── Wybór silnika ──────────────────────────────────────────────────────────────
# Zmień na False jeśli nie możesz zainstalować easyocr
USE_EASYOCR = True
# ──────────────────────────────────────────────────────────────────────────────


# ==============================================================================
# PREPROCESSING OPENCV — wspólny dla obu opcji
# ==============================================================================

def _preprocess_cv2(img: Image.Image) -> np.ndarray:
    """
    Lepszy preprocessing niż oryginalne ImageEnhance:
    - deskew (wyprostowanie przekrzywionego zdjęcia)
    - adaptive threshold (zamiast zwykłego kontrastu)
    - upscale do min 2400px szerokości
    Zwraca numpy array BGR gotowy do OCR.
    """
    import cv2

    img_np = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # ── Upscale ───────────────────────────────────────────────────────────────
    h, w = gray.shape
    if w < 2400:
        scale = 2400 / w
        gray = cv2.resize(
            gray, (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC
        )

    # ── Deskew — wyprostowanie przekrzywionego zdjęcia ────────────────────────
    gray = _deskew(gray)

    # ── Denoise ───────────────────────────────────────────────────────────────
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # ── Adaptive threshold — dużo lepszy niż prosty kontrast ──────────────────
    # Działa dobrze nawet przy niejednorodnym oświetleniu zdjęcia
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,   # rozmiar bloku (nieparzysta liczba)
        C=12,           # stała odejmowana od średniej
    )

    return thresh  # grayscale 0/255


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Wykrywa i koryguje obrót dokumentu (do ±15°)."""
    import cv2

    # Znajdź piksele tekstu
    coords = np.column_stack(np.where(gray < 200))
    if len(coords) < 100:
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Tylko małe kąty — nie ruszaj mocno przekręconych zdjęć (to może być celowe)
    if abs(angle) > 15:
        return gray

    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        gray, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


# ==============================================================================
# OPCJA A — EasyOCR (zalecana)
# ==============================================================================

def _get_easyocr_reader():
    """Singleton readera — modele ładowane raz i cachowane."""
    try:
        import streamlit as st

        @st.cache_resource(show_spinner="⏳ Ładowanie modelu EasyOCR (jednorazowo)…")
        def _load():
            import easyocr
            # pl + en — EasyOCR łączy oba modele
            return easyocr.Reader(["pl", "en"], gpu=False, verbose=False)

        return _load()
    except Exception:
        # Poza Streamlit (testy lokalne)
        import easyocr
        return easyocr.Reader(["pl", "en"], gpu=False, verbose=False)


def _ocr_easyocr(img: Image.Image) -> str:
    """
    OCR przez EasyOCR.
    Zwraca tekst gotowy do dalszego parsowania przez istniejące funkcje.
    """
    reader = _get_easyocr_reader()

    # Preprocessing
    try:
        processed = _preprocess_cv2(img)
        img_input = processed  # numpy array
    except Exception:
        img_input = np.array(img.convert("RGB"))

    # EasyOCR — paragraph=False daje lepsze wyniki dla tabelek z cyframi
    results = reader.readtext(
        img_input,
        detail=1,           # zwraca (bbox, text, confidence)
        paragraph=False,    # nie łącz w akapity — ważne dla tabelek!
        width_ths=0.7,
        height_ths=0.7,
    )

    if not results:
        return ""

    # Sortuj po pozycji Y (góra→dół), potem X (lewo→prawo)
    results_sorted = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))

    lines = []
    for bbox, text, conf in results_sorted:
        if conf > 0.2:  # odrzuć bardzo niepewne odczyty
            lines.append(text.strip())

    return "\n".join(lines)


# ==============================================================================
# OPCJA B — Tesseract z poprawionym preprocessingiem
# ==============================================================================

def _ocr_tesseract(img: Image.Image) -> str:
    """
    Tesseract z lepszym preprocessingiem OpenCV.
    Fallback jeśli EasyOCR niedostępny.
    """
    import pytesseract

    # Preprocessing
    try:
        processed = _preprocess_cv2(img)
        img_pil = Image.fromarray(processed)
    except Exception:
        # Jeśli cv2 niedostępne — stary preprocessing
        img_pil = img.convert("L")
        from PIL import ImageEnhance
        img_pil = ImageEnhance.Contrast(img_pil).enhance(2.0)

    # Tesseract z kilkoma trybami PSM — bierz najlepszy wynik (więcej cyfr)
    configs = [
        "--psm 6 --oem 1",   # uniform block (oryginał)
        "--psm 11 --oem 1",  # sparse text — lepiej dla tabelek
        "--psm 4 --oem 1",   # single column
    ]

    best_text = ""
    best_count = 0

    for cfg in configs:
        try:
            text = pytesseract.image_to_string(img_pil, lang="pol", config=cfg)
            # Policz znalezione 12-cyfrowe sekwencje
            count = len(re.findall(r"\d[\d\s\-]{9,}\d", text))
            if count > best_count:
                best_count = count
                best_text = text
        except Exception:
            continue

    return best_text if best_text else pytesseract.image_to_string(
        img_pil, lang="pol", config="--psm 6 --oem 1"
    )


# ==============================================================================
# PUBLICZNY INTERFEJS — identyczny jak oryginał
# ==============================================================================

def ocr_z_obrazu(img: Image.Image) -> str:
    """
    Drop-in replacement dla oryginalnej funkcji ocr_z_obrazu z app.py.
    Sygnatura identyczna: Image.Image → str
    """
    if USE_EASYOCR:
        try:
            return _ocr_easyocr(img)
        except ImportError:
            # EasyOCR niezainstalowany — fallback na Tesseract
            pass
        except Exception as e:
            # Inny błąd EasyOCR — fallback
            print(f"[EasyOCR error] {e} — używam Tesseract")

    return _ocr_tesseract(img)


# ==============================================================================
# BONUS — lepsza ekstrakcja numerów wagonów
# Wklej do app.py zamiast oryginalnych _znajdz_wagony_raw + formatuj_wagon
# ==============================================================================

def formatuj_wagon(cyfry: str) -> str:
    """Formatuje 12 cyfr → '3351 5332 137-7'."""
    d = re.sub(r"\D", "", cyfry)[:12]
    if len(d) < 12:
        return cyfry
    return f"{d[0:4]} {d[4:8]} {d[8:11]}-{d[11]}"


def _znajdz_wagony_raw(text: str) -> list:
    """
    Ulepszona wersja — obsługuje dodatkowe wzorce z EasyOCR:
    - cyfry rozdzielone spacjami (z tabelki: "3 3 5 1 5 3 3 2 1 3 7 7")
    - cyfry przyklejone
    - cyfry z myślnikami
    """
    found, seen = [], set()

    # Wzorzec 1: Cyfry przyklejone lub rozdzielone myślnikami/spacjami
    text_clean = re.sub(r"(?m)^\s*\d{1,2}[\.\)\s]\s*", " ", text)

    # Wzorzec 2: sekwencja dokładnie 12 cyfr po jednej ze spacjami
    # np. "3 3 5 1 5 3 3 2 1 3 7 7" — typowe wyjście EasyOCR z tabelki
    for m in re.finditer(
        r"\b(\d\s){11}\d\b",   # 12 cyfr rozdzielonych spacjami
        text_clean
    ):
        raw = re.sub(r"\D", "", m.group(0))
        if len(raw) == 12 and raw not in seen and not _czy_telefon(raw):
            seen.add(raw)
            found.append(raw)

    # Wzorzec 3: standardowy (przyklejone cyfry)
    for m in re.finditer(r"\b(\d[\d\s\-\.]{9,16}\d)\b", text_clean):
        raw = re.sub(r"\D", "", m.group(1))
        if len(raw) == 12 and raw not in seen and not _czy_telefon(raw):
            seen.add(raw)
            found.append(raw)

    return found


def _czy_telefon(raw: str) -> bool:
    """Odrzuca numery telefonów."""
    prefiksy_tel = ("48", "881", "882", "535", "538", "500", "501",
                    "502", "503", "504", "505", "506", "507", "508", "509")
    return any(raw.startswith(p) for p in prefiksy_tel)


# ==============================================================================
# TEST LOKALNY
# ==============================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Użycie: python ocr_fix_free.py <ścieżka_do_zdjęcia>")
        sys.exit(1)

    path = sys.argv[1]
    img = Image.open(path)

    print(f"Silnik: {'EasyOCR' if USE_EASYOCR else 'Tesseract+OpenCV'}")
    print("=" * 60)
    tekst = ocr_z_obrazu(img)
    print(tekst)
    print("=" * 60)

    wagony = _znajdz_wagony_raw(tekst)
    print(f"\nZnalezione wagony ({len(wagony)}):")
    for w in wagony:
        print(f"  → {formatuj_wagon(w)}")
