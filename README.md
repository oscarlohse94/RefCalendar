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
