# RefCalendar
Automation to add the RefSoft appointments to the google calendar

## Installation

### Windows

Installiere zuerst Python 3.10 oder neuer mit dem Python-Installer (ggf. mit
dem `py`-Launcher und `pip`). Fuehre die Einrichtung anschlie&szlig;end in
PowerShell aus dem Repository-Ordner aus:

```bash
. .\setup.ps1
```

Das Skript muss mit Punkt und Leerzeichen eingebunden werden, damit es
`.venv` in der aktuellen PowerShell aktivieren kann. Falls PowerShell die
Ausfuehrung blockiert, einmalig den aktuellen Prozess erlauben:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Das Skript fragt nach der persoenlichen DHB-URL und erstellt oder aktualisiert
die Benutzerkonfiguration unter `%LOCALAPPDATA%\RefCalendar\config.env`. Die
Eingabe kann mit Strg+V eingefuegt werden, wird dabei aber im
Terminal angezeigt. Falls Strg+V in der PowerShell-Konsole nicht funktioniert,
kopiere den Link vorher und gib an der Abfrage `CLIPBOARD` ein. Dann verwendet
das Skript `.venv\Scripts\python.exe` und installiert das Projekt per pip.

Windows-Befehle verwenden daher:

```powershell
.venv\Scripts\python.exe -m main
.venv\Scripts\python.exe -m unittest discover -s python/tests -t python -p "test_*.py" -v
```

### Linux, WSL oder macOS

Das Skript muss eingebunden werden, damit es `.venv` in der aktuellen Shell
aktivieren kann:

```bash
source ./setup.sh
```

## Preview calendar JSON

Run the application from the repository root to fetch the DHB assignments and
print a formatted JSON array of Google Calendar events:

```bash
.venv/bin/python -m main
```

On Windows:

```powershell
.venv\Scripts\python.exe -m main
```

The output includes referee names and available contact details. Treat it as
personal data when copying, saving, or sharing the console output.

## Desktop UI prototype

Start the initial Windows interface from the repository root:

```powershell
.\.venv\Scripts\python.exe -m desktop_app
```

In this draft, saving a DHB link fetches its page, detects the referee name,
stores both values in the per-user configuration, and displays the parsed games. The last parsed
games are cached per Windows user under `%LOCALAPPDATA%\RefCalendar` and shown
again when the app starts. Sync fetches the latest DHB data and updates Google
Calendar in the background. Google connection management, disconnect, and
autostart controls are still placeholders.

The personal configuration and Google token are stored separately from the
project under `%LOCALAPPDATA%\RefCalendar`.

## Sync to Google Calendar

1. In Google Cloud, enable the Google Calendar API and create an OAuth client
   with application type **Desktop app**. The app-level `credentials.json`
   remains beside the project for now; it is not user-specific.
2. Save the OAuth client configuration as `credentials.json` in the repository
   root. If the Console does not offer a JSON download, add a new client secret
   and create the standard Desktop app JSON configuration manually. This file
   is ignored by Git and must be kept private.
3. Test the login and read access without changing calendar data:

   ```bash
   .venv/bin/python -m main --test-google-login
   ```

   On Windows:

   ```powershell
   .venv\Scripts\python.exe -m main --test-google-login
   ```

   On first run, open the authorization URL printed in the terminal in your
   browser and authorize RefCalendar. The refresh token is stored under
   `%LOCALAPPDATA%\RefCalendar\token.json`. The test only requests up to one event ID
   and does not print it or modify events.

4. When ready to create or update events, use the explicit sync flag:

   ```bash
   .venv/bin/python -m main --sync-calendar
   ```

   On Windows:

   ```powershell
   .venv\Scripts\python.exe -m main --sync-calendar
   ```

The sync targets the primary calendar. Events use a stable Google event ID
derived from the DHB game number: a repeated run updates the existing event
instead of creating another copy. The sync command writes to Google Calendar;
without `--sync-calendar`, the application only prints the JSON preview.

## Tests

The tests use Python's built-in `unittest` framework. Run the full suite from
the repository root:

```bash
.venv/bin/python -m unittest discover -s python/tests -t python -p 'test_*.py' -v
```

On Windows:

```powershell
.venv\Scripts\python.exe -m unittest discover -s python/tests -t python -p "test_*.py" -v
```

The `python/tests` directory groups tests by component. For example,
`python/tests/html_to_data/test_html_to_data.py` covers parsing HTML into the
data model. These tests use small HTML samples and do not fetch the DHB page or
require a `.env` file.

The `-t python` option makes the `python` directory the import root, matching
the application's current module layout.

Using `--without-pip` avoids needing the OS `python3-venv` package when its
package repository is unavailable.
