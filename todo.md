# TODO — Holter 12-odprowadzeniowy

## Obecne ograniczenia

- Cechy QRS i pre-QRS są jedynie prostymi estymatami do preselekcji; nie zastępują zwalidowanej analizy morfologii ani P-wave.
- PVC, PAC/SVEB, AF i SVT nie są jeszcze rozpoznawane w sposób wystarczający do zastosowania klinicznego.
- Zgodność QRS wykorzystuje wyłącznie osiem niezależnie mierzonych kanałów ADS1298, ale wymaga walidacji z referencją.
- Ocena jakości sygnału ma charakter bramki technicznej i wymaga kalibracji na docelowym rejestratorze.

## Kolejne kroki

1. Rozszerzyć estymację P-wave i morfologii QRS o algorytm zwalidowany na wieloodprowadzeniowych Holterach.
2. Dodać testy integracyjne na anotowanych holterach, także dla zdarzeń na granicach fragmentów.
3. Ustalić kliniczne definicje epizodów i progi wraz z elektrofizjologiem/kardiologiem.
4. Przed zastosowaniem klinicznym przeprowadzić niezależną walidację czułości, PPV, błędów per-arytmia i jakości zapisu.
