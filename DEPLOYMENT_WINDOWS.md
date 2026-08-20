# Uruchomienie aplikacji EKG jako serwer w sieci lokalnej (Windows)

Ten dokument opisuje, jak postawić aplikację na komputerze z Windows tak, aby
inne urządzenia w tej samej sieci (np. tablet w gabinecie) mogły otworzyć ją
w przeglądarce pod adresem `http://<IP-komputera>:8000`.

Domyślny serwer deweloperski Flaska (`app.run()`) **nie nadaje się** do
pracy ciągłej — używamy zamiast niego **Waitress**, czystopythonowego
serwera WSGI, który działa natywnie na Windows (Gunicorn tego nie robi).

## 1. Przygotowanie środowiska

```powershell
cd C:\sciezka\do\projektu
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Upewnij się, że w projekcie są też katalogi `templates/` i `static/css/`
(dołączone w tej dostawie) oraz Twój istniejący pakiet `arrhythmia/`.

## 2. Szybki test

```powershell
venv\Scripts\activate
python serve.py
```

Powinieneś zobaczyć:

```
Serwer EKG nasłuchuje na http://0.0.0.0:8000 (Ctrl+C aby zatrzymać)
```

Otwórz `http://localhost:8000` w przeglądarce na tym samym komputerze —
powinien pojawić się formularz uploadu.

## 3. Udostępnienie w sieci lokalnej

1. Sprawdź adres IP komputera: `ipconfig` (pozycja "Adres IPv4", np. `192.168.1.50`).
2. Dodaj regułę zapory sieciowej, żeby inne urządzenia mogły się połączyć:

   ```powershell
   netsh advfirewall firewall add rule name="Analiza EKG" dir=in action=allow protocol=TCP localport=8000
   ```

3. Z innego urządzenia w tej samej sieci Wi-Fi/LAN wejdź na:
   `http://192.168.1.50:8000` (podmień na swój adres IP).

> Aplikacja nie ma obecnie żadnego logowania/autoryzacji — nadaje się do
> zamkniętej sieci lokalnej. Jeśli planujesz udostępnić ją poza siecią
> lokalną (internet), koniecznie dodaj uwierzytelnianie i HTTPS (np. przez
> reverse proxy typu Caddy/nginx) zanim to zrobisz — dane pacjentów nie
> powinny latać po sieci bez zabezpieczeń.

## 4. Automatyczne uruchamianie jako usługa Windows (NSSM)

Żeby serwer działał w tle i startował razem z komputerem (również gdy nikt
nie jest zalogowany), najprościej opakować go w usługę Windows za pomocą
**NSSM** (Non-Sucking Service Manager, darmowe narzędzie).

1. Pobierz NSSM: https://nssm.cc/download i rozpakuj (np. do `C:\nssm`).
2. Zainstaluj usługę (z uprawnieniami administratora):

   ```powershell
   C:\nssm\win64\nssm.exe install AnalizaEKG "C:\sciezka\do\projektu\venv\Scripts\python.exe" "C:\sciezka\do\projektu\serve.py"
   C:\nssm\win64\nssm.exe set AnalizaEKG AppDirectory "C:\sciezka\do\projektu"
   C:\nssm\win64\nssm.exe set AnalizaEKG Start SERVICE_AUTO_START
   C:\nssm\win64\nssm.exe set AnalizaEKG AppStdout "C:\sciezka\do\projektu\logs\stdout.log"
   C:\nssm\win64\nssm.exe set AnalizaEKG AppStderr "C:\sciezka\do\projektu\logs\stderr.log"
   ```

   (utwórz najpierw folder `logs`, jeśli chcesz logi do plików)

3. Uruchom usługę:

   ```powershell
   C:\nssm\win64\nssm.exe start AnalizaEKG
   ```

4. Sprawdź w `services.msc`, czy usługa "AnalizaEKG" ma status "Uruchomiona"
   i typ startu "Automatyczny".

Przydatne komendy:

```powershell
nssm restart AnalizaEKG   # restart po zmianie kodu
nssm stop AnalizaEKG      # zatrzymanie
nssm remove AnalizaEKG confirm   # odinstalowanie usługi
```

### Alternatywa bez NSSM

Jeśli nie chcesz instalować dodatkowego narzędzia, możesz dodać zadanie w
**Harmonogramie zadań Windows** (Task Scheduler) uruchamiane "przy starcie
systemu", wywołujące `venv\Scripts\pythonw.exe serve.py`. Jest to prostsze,
ale w razie awarii procesu Windows go automatycznie nie zrestartuje (NSSM
to robi) — dlatego NSSM jest zalecany do pracy produkcyjnej.

## 5. Aktualizacja aplikacji

Po zmianach w kodzie:

```powershell
nssm restart AnalizaEKG
```

## 6. Porządkowanie plików

Każda analiza zapisuje plik CSV w `uploads/` oraz dwa wykresy PNG w
`static/plots/` z unikalnym identyfikatorem — te katalogi będą rosnąć w
nieskończoność. Warto dodać okresowe czyszczenie (np. zaplanowane zadanie
usuwające pliki starsze niż N dni), jeśli aplikacja ma działać długoterminowo.
