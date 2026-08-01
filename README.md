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

## Obecny zakres analizy

Aplikacja oznacza potencjalne: tachykardię, bradykardię, nieregularność RR sugerującą AF, PVC, PAC/SVEB, SVT, pauzy, bigeminię i trigeminię. To są reguły demonstracyjne, które wymagają walidacji na opisanych danych klinicznych.

## Struktura

- `app.py` — interfejs Flask i obsługa plików,
- `main.py` — przepływ analizy,
- `arrhythmia/` — reguły detekcji,
- `dane/` — przykładowe zapisy EKG,
- `templates/` — widoki strony.
