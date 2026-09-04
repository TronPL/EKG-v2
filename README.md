# EKG Analyzer — preselekcja zapisu Holtera

Prototyp aplikacji webowej do automatycznej preselekcji jedno- i wieloodprowadzeniowych zapisów EKG/Holtera. Aplikacja nie wydaje rozpoznań; tworzy listę fragmentów, które powinny zostać ocenione przez osobę z odpowiednimi kwalifikacjami klinicznymi.

> Wynik automatyczny nie jest diagnozą medyczną, nie może służyć jako jedyna podstawa decyzji klinicznej i nie zastępuje certyfikowanego oprogramowania medycznego.

## Co robi obecna wersja

- Wczytuje CSV/TXT z jednym kanałem albo osiem fizycznie rejestrowanych kanałów ADS1298 (`I`, `II`, `V1`–`V6`). Z ośmiu kanałów wylicza też standardowe odprowadzenia pochodne `III`, `aVR`, `aVL` i `aVF` do podglądu.
- Przetwarza długie zapisy porcjami, zachowując kontekst na granicach bloków i bez wczytywania całego Holtera do pamięci.
- Sprawdza równomierność znaczników czasu; zapis z lukami lub znacznym jitterem jest odrzucany, aby nie zafałszować odstępów RR.
- Ocenia jakość sygnału osobno dla każdego fizycznego kanału: płaski sygnał, nadmierny szum próbka-po-próbce i clipping.
- Dla ADS1298 wykrywa QRS w kanałach o wystarczającej jakości i uzgadnia pozycje QRS między niezależnymi kanałami. Odprowadzenia pochodne nie są niezależnymi głosami. Brak zgodności jest widoczny w raporcie jako użycie trybu awaryjnego odprowadzenia II.
- Wyznacza pomocnicze cechy pobudzenia: szacowaną szerokość QRS, podobieństwo morfologii i cechę pre-QRS z II/V1. Są one wyłącznie wsparciem dla priorytetyzacji przeglądu.
- Oznacza w 30-sekundowych, przesuwanych oknach kandydatów do tachykardii, bradykardii, możliwego AF (nieregularne RR bez potwierdzenia P-wave) oraz regularnej szybkiej tachykardii zgodnej z możliwym SVT.
- Oznacza pauzy oraz wcześniejsze pobudzenia. PVC jest etykietowane wyłącznie przy zmianie morfologii QRS; PAC/SVEB wymaga wąskiego QRS i pomocniczej cechy pre-QRS. W pozostałych przypadkach pozostaje neutralna etykieta „niejednoznaczne”.
- Pokazuje 30-sekundowy podgląd, przegląd dowolnego fragmentu oraz kontekst zdarzenia. Dla danych ADS1298 widok zdarzenia zawiera również 12-odprowadzeniowe EKG.

## Czego program jeszcze nie zapewnia

Progi jakości, QRS, cech morfologii i epizodów są inżynierskimi ustawieniami testowymi. Nie zostały niezależnie zwalidowane na anotowanych Holterach ani zatwierdzone dla konkretnego rejestratora, populacji i zastosowania. W szczególności AF/AFL, SVT/VT, PVC/PAC oraz załamki P nie mogą być uznawane za wiarygodnie rozpoznane bez oceny klinicznej i programu walidacji.

Szczegółowy plan walidacji i dalszych prac znajduje się w [todo.md](todo.md). Przed użyciem klinicznym wymagane są m.in. definicja przeznaczenia, analiza ryzyka, dane anotowane przez ekspertów, niezależna ocena skuteczności i proces zgodności dla oprogramowania medycznego.

## Uruchomienie

W katalogu projektu utwórz aktywne środowisko Python i zainstaluj zależności:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Następnie otwórz adres pokazany przez aplikację (zwykle `http://127.0.0.1:5000`). Do pracy produkcyjnej w sieci lokalnej zobacz [DEPLOYMENT_WINDOWS.md](DEPLOYMENT_WINDOWS.md).

## Format pliku wejściowego

Akceptowane są pliki CSV i TXT o separatorze `;` lub `,`.

### Jeden kanał

Pierwsze dwie kolumny to czas w sekundach i amplituda EKG:

```text
0.000;0.03289
0.004;0.00422
0.008;0.01017
```

### ADS1298: osiem kanałów i widok 12-odprowadzeniowy

Plik ma dziewięć kolumn: czas i osiem kanałów. Użyj nagłówków `I`, `II`, `V1`–`V6` albo `CH1`–`CH8` w tej kolejności:

```text
time;I;II;V1;V2;V3;V4;V5;V6
0.000;...;...;...;...;...;...;...;...
```

Wymagane przypisanie sprzętowe to `CH1 = I`, `CH2 = II`, `CH3–CH8 = V1–V6` względem WCT. Pełny opis połączeń i wzorów: [docs/ads1298_12lead.md](docs/ads1298_12lead.md).

## Dane testowe

Dołączony plik [dane/holter_test_30min_100Hz_arytmie.csv](dane/holter_test_30min_100Hz_arytmie.csv) to syntetyczny, 30-minutowy zapis ADS1298 o częstotliwości 100 Hz. Nie reprezentuje danych pacjenta i nie nadaje się do walidacji klinicznej. Służy do testowania importu, przetwarzania blokowego, widoków oraz regresji algorytmu.

Zaplanowane fragmenty (czas od początku zapisu):

| Czas | Zawartość syntetyczna | Oczekiwane oznaczenie do przeglądu |
| --- | --- | --- |
| 0–300 s | rytm miarowy ok. 75/min | brak epizodu |
| 300–480 s | rytm miarowy ok. 120/min | tachykardia |
| 780–1020 s | nieregularne RR | możliwe AF |
| 1020–1140 s | rytm ok. 46/min | bradykardia |
| 1200–1290 s | przedwczesne szerokie i wąskie pobudzenia | PVC/PAC-SVEB lub pobudzenie niejednoznaczne |
| około 1370 s | odstęp RR 2,6 s | pauza |
| 1500–1560 s | rytm miarowy ok. 171/min | możliwe SVT i tachykardia |

Wynik może różnić się na granicach syntetycznych odcinków, ponieważ algorytm działa zachowawczo i wymaga cech sygnału, a nie tylko harmonogramu generatora. Źródło danych można odtworzyć skryptem [tools/generate_synthetic_holter.py](tools/generate_synthetic_holter.py).

## Struktura projektu

- `app.py` — interfejs Flask, zapis wyników i widoki przeglądu;
- `main.py` — strumieniowy przebieg analizy;
- `signal_quality.py` — bramka jakości kanałów;
- `qrs_consensus.py` — uzgadnianie QRS między kanałami;
- `morphology.py` — pomocnicze cechy pobudzeń;
- `arrhythmia/episodes.py` — detekcja kandydatów epizodycznych w oknach;
- `io_utils.py`, `leads.py` — import danych i definicje odprowadzeń;
- `tests/` — testy importu, odprowadzeń i reguł preselekcji;
- `dane/` — przykładowe oraz syntetyczne zapisy EKG.
