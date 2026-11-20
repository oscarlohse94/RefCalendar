# RefCalendar
Automation to add the RefSoft appointments to the google calendar

## Installation

On Linux, WSL, or macOS, run the setup script from the repository:

```bash
source ./setup.sh
```

The script must be sourced so it can activate `.venv` in the current shell.
It asks for the personal DHB URL without echoing it: enter a new URL to update
`.env`, or press Enter to keep the current value. If `.env` does not exist, a
URL is required to create it with owner-only permissions. An existing valid
`.venv` is reused; otherwise, the script creates it without bootstrapping
`pip` and installs the project dependencies into it.

## Preview calendar JSON

Run the application from the repository root to fetch the DHB assignments and
print a formatted JSON array of Google Calendar events:

```bash
.venv/bin/python -m main
```

The output includes referee names and available contact details. Treat it as
personal data when copying, saving, or sharing the console output.

## Sync to Google Calendar

1. In Google Cloud, enable the Google Calendar API and create an OAuth client
   with application type **Desktop app**.
2. Save the downloaded client file as `credentials.json` in the repository
   root. This file is ignored by Git.
3. Test the login and read access without changing calendar data:

   ```bash
   .venv/bin/python -m main --test-google-login
   ```

   On first run, open the authorization URL printed in the terminal in your
   browser and authorize RefCalendar. The refresh token is stored locally in
   `token.json`, also ignored by Git. The test only requests up to one event ID
   and does not print it or modify events.

4. When ready to create or update events, use the explicit sync flag:

   ```bash
   .venv/bin/python -m main --sync-calendar
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

The `python/tests` directory groups tests by component. For example,
`python/tests/html_to_data/test_html_to_data.py` covers parsing HTML into the
data model. These tests use small HTML samples and do not fetch the DHB page or
require a `.env` file.

The `-t python` option makes the `python` directory the import root, matching
the application's current module layout.

Using `--without-pip` avoids needing the OS `python3-venv` package when its
package repository is unavailable.
