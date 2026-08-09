# EKG Analyzer

Prototyp aplikacji webowej do przesiewowej analizy jednoodprowadzeniowych zapisów EKG/Holtera. Aplikacja oczyszcza sygnał, wykrywa załamki R i oznacza zdarzenia według prostych reguł opartych na odstępach RR.

> Wynik nie jest diagnozą medyczną i nie może zastąpić oceny lekarza ani certyfikowanego oprogramowania medycznego.

## Uruchomienie

W katalogu projektu utwórz i aktywuj środowisko wirtualne, a następnie zainstaluj zależności:

```powershell
python -m venv .venv
# Najczęściej w Windows:
.\.venv\Scripts\Activate.ps1
# Jeśli środowisko zostało utworzone z katalogiem "bin":
# .\.venv\bin\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Następnie otwórz w przeglądarce adres wyświetlony przez Flask (zwykle `http://127.0.0.1:5000`). W czasie lokalnego rozwoju można włączyć szczegółowy tryb diagnostyczny przez ustawienie `FLASK_DEBUG=1`.

## Format danych wejściowych

Wgrywany plik musi być plikiem CSV lub TXT o maksymalnym rozmiarze 20 MB. Pierwsze dwie kolumny muszą zawierać kolejno:

1. czas w sekundach (rosnąco),
2. amplitudę EKG.

Akceptowane są separatory `;` i `,`. Wiersz nagłówka oraz dodatkowe kolumny są dopuszczalne i ignorowane. Częstotliwość próbkowania jest wyznaczana z kolumny czasu.

Przykład:

```text
0.000;0.03289
0.002;0.00422
0.004;0.01017
```

### ADS1298: 8 kanałów → 12 odprowadzeń

Plik wielokanałowy zawiera dziewięć kolumn: czas i osiem kanałów ADS1298. Dopuszczalne są dwa nagłówki:

```text
time;CH1;CH2;CH3;CH4;CH5;CH6;CH7;CH8
```

albo:

```text
time;I;II;V1;V2;V3;V4;V5;V6
```

Wymagane przypisanie sprzętowe to CH1 = I, CH2 = II oraz CH3–CH8 = V1–V6 względem WCT. Aplikacja oblicza cyfrowo III, aVR, aVL i aVF z I oraz II. Pełny opis połączeń, wzorów i ograniczeń znajduje się w [docs/ads1298_12lead.md](docs/ads1298_12lead.md).

## Obecny zakres analizy

Aplikacja oznacza potencjalne: tachykardię, bradykardię, nieregularność RR sugerującą AF, PVC, PAC/SVEB, SVT, pauzy, bigeminię i trigeminię. To są reguły demonstracyjne, które wymagają walidacji na opisanych danych klinicznych.

## Struktura

- `app.py` — interfejs Flask i obsługa plików,
- `main.py` — przepływ analizy,
- `arrhythmia/` — reguły detekcji,
- `dane/` — przykładowe zapisy EKG,
- `templates/` — widoki strony.
- `leads.py` — definicje i wyliczanie standardowych 12 odprowadzeń,
- `docs/ads1298_12lead.md` — konfiguracja ADS1298 dla 12 odprowadzeń.
