W ramach projektu należy przygotować program będący grą w pokera.
Użytkownik gra przeciwko 3 graczom sterowanym przez komputer (oczywiście sposób gry komputera może być maksymalnie uproszczony - karty po kolei, pary, trójki). Wymagania:
Projekt musi być napisany obiektowo, z przechowywaniem wyników w plikach plus interfejs graficzny webowy.

## Uruchomienie

Gra to poker dobierany (5-card draw) napisany w całości w Pythonie — interfejs webowy zbudowano przy użyciu NiceGUI (bez kodu JavaScript).

```bash
pip install -r requirements.txt
python main.py
```

Następnie otwórz `http://localhost:8080` w przeglądarce.

### Jak grać

1. **Dobieranie** — kliknij karty, które chcesz wymienić (maks. 3), a następnie naciśnij
   **Dobierz**. Bez zaznaczeń przycisk pozwala zostać przy układzie.
2. **Licytacja** — po dobraniu wybierz akcję: Pas / Czek / Sprawdź / Stawiaj / Podbij.
3. **Rozstrzygnięcie** — najlepszy 5-kartowy układ wygrywa pulę (remis dzieli pulę).
4. **Pobierz wyniki** — eksportuje historię rozdań i żetonów do pliku JSON.

