# ADS1298: 8 kanałów do standardowego EKG 12‑odprowadzeniowego

## Najważniejsze założenie

ADS1298 ma osiem jednocześnie próbkowanych kanałów ADC. W standardowym EKG 12‑odprowadzeniowym nie potrzeba dwunastu niezależnych pomiarów: zapisuje się osiem odprowadzeń bezpośrednich, a cztery kończynowe oblicza się cyfrowo.

Ta aplikacja przyjmuje wyłącznie następującą konfigurację:

| Kanał ADS1298 | Zapis w CSV | Co musi mierzyć sprzęt |
| --- | --- | --- |
| CH1 | I | LA − RA |
| CH2 | II | LL − RA |
| CH3 | V1 | V1 − WCT |
| CH4 | V2 | V2 − WCT |
| CH5 | V3 | V3 − WCT |
| CH6 | V4 | V4 − WCT |
| CH7 | V5 | V5 − WCT |
| CH8 | V6 | V6 − WCT |

`RA` oznacza prawą rękę, `LA` lewą rękę, `LL` lewą nogę. `RL` (prawa noga) jest elektrodą RLD/pacjenta i **nie jest** jednym z dwunastu odprowadzeń. `WCT` to końcówka centralna Wilsona:

```text
WCT = (RA + LA + LL) / 3
```

ADS1298 ma sprzętowy blok WCT; dokumentacja TI opisuje go jako odniesienie dla odprowadzeń przedsercowych i potwierdza, że w typowej konfiguracji ośmiokanałowej odprowadzenia wzmocnione liczy się cyfrowo. [Datasheet ADS1298, sekcje WCT i augmented leads](https://www.ti.com/lit/ds/symlink/ads1298.pdf)

## Co program wylicza

Program zapisuje osiem kanałów bezpośrednich i oblicza cztery odprowadzenia kończynowe:

| Odprowadzenie | Wzór | Charakter widoku |
| --- | --- | --- |
| I | `LA − RA` — CH1 | boczny wysoki |
| II | `LL − RA` — CH2 | dolny; używane przez program do analizy rytmu |
| III | `II − I = LL − LA` | dolny |
| aVR | `−(I + II) / 2` | z prawego barku / górny prawy |
| aVL | `I − II / 2` | boczny wysoki |
| aVF | `II − I / 2` | dolny |
| V1 | `V1 − WCT` — CH3 | przegroda / prawa część serca |
| V2 | `V2 − WCT` — CH4 | przegroda |
| V3 | `V3 − WCT` — CH5 | ściana przednia |
| V4 | `V4 − WCT` — CH6 | ściana przednia / okolica koniuszka |
| V5 | `V5 − WCT` — CH7 | ściana boczna |
| V6 | `V6 − WCT` — CH8 | ściana boczna |

Wzór dla III wynika z prawa Einthovena: `II = I + III`.

## Pozycje elektrod przedsercowych

| Elektroda | Pozycja |
| --- | --- |
| V1 | czwarta przestrzeń międzyżebrowa, prawy brzeg mostka |
| V2 | czwarta przestrzeń międzyżebrowa, lewy brzeg mostka |
| V3 | w połowie drogi między V2 i V4 |
| V4 | piąta przestrzeń międzyżebrowa, linia środkowo‑obojczykowa lewa |
| V5 | na tym samym poziomie co V4, lewa linia pachowa przednia |
| V6 | na tym samym poziomie co V4, lewa linia pachowa środkowa |

## Format CSV

```text
time;CH1;CH2;CH3;CH4;CH5;CH6;CH7;CH8
0.000;0.012;0.021;0.005;0.006;0.008;0.010;0.011;0.009
0.002;0.013;0.023;0.006;0.008;0.009;0.012;0.012;0.010
```

Wartości kanałów muszą być już przeliczone przez firmware z kodu ADC na jedną, spójną jednostkę amplitudy (np. mV). Jeśli plik zawiera surowe 24‑bitowe kody ADC, najpierw należy przeliczyć je z użyciem rzeczywiście ustawionych `VREF` i wzmocnienia PGA. Aplikacja nie konfiguruje rejestrów ADS1298 ani nie wykonuje tej kalibracji.

## Co implementuje aplikacja, a czego nie

- Oblicza cztery odprowadzenia pochodne dokładnie z powyższych wzorów.
- Tworzy przegląd wszystkich dwunastu odprowadzeń w układzie 3 × 4 z pierwszych 10 sekund nagrania.
- Analizuje rytm na pełnej długości odprowadzenia II.
- Nie potwierdza klinicznie rozpoznań i nie zastępuje certyfikowanego oprogramowania EKG.
- Nie może naprawić błędnego podłączenia elektrod, odwróconej polaryzacji, braku WCT ani artefaktów ruchowych.

## Pliki całodobowe

Obecny limit aplikacji wynosi 20 MB, a moduł analizy wczytuje plik w całości do pamięci. To wystarcza do krótkich zapisów testowych, ale nie do pełnego, ośmiokanałowego Holtera 24 h. Obsługa doby wymaga kolejnego etapu: importu porcjami, analizy w oknach czasowych i raportu zbiorczego. Nie należy podnosić samego limitu uploadu bez tej przebudowy, ponieważ przeglądarka i proces Pythona mogłyby zużyć zbyt dużo pamięci.

Przed użyciem z osobą badaną należy porównać zapis z referencyjnym symulatorem EKG lub zwalidowanym aparatem 12‑odprowadzeniowym. Nie należy podejmować decyzji klinicznych wyłącznie na podstawie tego programu.
