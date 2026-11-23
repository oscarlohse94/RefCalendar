#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'Bitte in der aktuellen Bash-Shell mit "source ./setup.sh" starten.\n' >&2
    exit 1
fi

_refcalendar_private_setup() {
    local root_dir="$1"
    local config_directory=""
    local env_file=""
    local venv_dir="$root_dir/.venv"
    local dhb_url=""
    local pip_help=""
    local python_cmd=""

    case "$(uname -s)" in
        Darwin*)
            config_directory="$HOME/Library/Application Support/RefCalendar"
            ;;
        *)
            config_directory="${XDG_CONFIG_HOME:-$HOME/.config}/refcalendar"
            ;;
    esac
    env_file="$config_directory/config.env"
    if ! mkdir -p "$config_directory"; then
        printf 'Fehler: RefCalendar-Benutzerordner konnte nicht erstellt werden.\n' >&2
        return 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        printf 'Fehler: python3 wurde nicht gefunden.\n' >&2
        return 1
    fi

    if ! python_cmd="$(python3 -c 'import sys; print(sys._base_executable)')"; then
        printf 'Fehler: Der verwendete Python-Interpreter konnte nicht ermittelt werden.\n' >&2
        return 1
    fi
    if [[ -z "$python_cmd" ]]; then
        printf 'Fehler: Der verwendete Python-Interpreter konnte nicht ermittelt werden.\n' >&2
        return 1
    fi

    if ! "$python_cmd" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
        printf 'Fehler: RefCalendar benötigt Python 3.10 oder neuer.\n' >&2
        return 1
    fi

    if ! pip_help="$("$python_cmd" -m pip --help 2>/dev/null)"; then
        printf 'Fehler: System-Python benötigt pip, um Pakete in .venv zu installieren.\n' >&2
        return 1
    fi
    if [[ "$pip_help" != *"--python"* ]]; then
        printf 'Fehler: Die installierte pip-Version unterstützt die Option --python nicht.\n' >&2
        return 1
    fi
    unset pip_help

    if [[ ! -t 0 ]]; then
        printf 'Fehler: Für die URL-Abfrage muss das Skript interaktiv geladen werden.\n' >&2
        return 1
    fi

    if [[ -e "$env_file" ]]; then
        printf 'Neue persönliche DHB-URL eingeben oder Enter zum Beibehalten (Eingabe bleibt unsichtbar): '
    else
        printf 'Persönliche DHB-URL eingeben (Eingabe bleibt unsichtbar): '
    fi
    if ! IFS= read -r -s dhb_url; then
        printf '\nFehler: Die URL konnte nicht gelesen werden.\n' >&2
        return 1
    fi
    printf '\n'

    if [[ -n "$dhb_url" ]]; then
        if [[ ! "$dhb_url" =~ ^https://dhb\.refsoft\.de/api/index\.php\?m=.+$ ]]; then
            printf 'Fehler: Die URL hat nicht das erwartete DHB-Format. Die Konfigurationsdatei blieb unverändert.\n' >&2
            return 1
        fi

        if ! REFCALENDAR_NEW_DHB_URL="$dhb_url" "$python_cmd" - "$env_file" <<'PY'
import os
import re
import sys
import tempfile
from pathlib import Path

target = Path(sys.argv[1])
new_url = os.environ["REFCALENDAR_NEW_DHB_URL"]
content = target.read_text(encoding="utf-8") if target.exists() else ""
url_assignment = re.compile(r"^\s*(?:export\s+)?DHB_URL\s*=")
updated_lines = []
replaced = False

for line in content.splitlines(keepends=True):
    if url_assignment.match(line):
        if not replaced:
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            updated_lines.append(f"DHB_URL={new_url}{ending}")
            replaced = True
    else:
        updated_lines.append(line)

if not replaced:
    if updated_lines and not updated_lines[-1].endswith(("\n", "\r")):
        updated_lines[-1] += "\n"
    updated_lines.append(f"DHB_URL={new_url}\n")

temp_name = None
try:
    file_descriptor, temp_name = tempfile.mkstemp(prefix=".env.", dir=target.parent)
    with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as temp_file:
        temp_file.writelines(updated_lines)
    os.chmod(temp_name, 0o600)
    os.replace(temp_name, target)
finally:
    if temp_name is not None and os.path.exists(temp_name):
        os.unlink(temp_name)
PY
        then
            printf 'Fehler: Die DHB-URL konnte nicht in der Benutzerkonfiguration gespeichert werden.\n' >&2
            return 1
        fi
        printf 'DHB-URL in Benutzerkonfiguration aktualisiert.\n'
    elif [[ -e "$env_file" ]]; then
        printf 'Bisherige DHB-URL bleibt unverändert.\n'
    else
        printf 'Fehler: Ohne eine DHB-URL kann keine Konfigurationsdatei erstellt werden.\n' >&2
        return 1
    fi

    if [[ ! -x "$venv_dir/bin/python" ]]; then
        if [[ -e "$venv_dir" ]]; then
            printf 'Fehler: .venv existiert, enthält aber keinen funktionsfähigen Python-Interpreter. Bitte prüfe sie manuell.\n' >&2
            return 1
        fi
        if ! "$python_cmd" -m venv --without-pip "$venv_dir"; then
            printf 'Fehler: .venv konnte nicht erstellt werden.\n' >&2
            return 1
        fi
        printf '.venv wurde erstellt.\n'
    else
        printf 'Vorhandene .venv wird weiterverwendet.\n'
    fi

    if ! "$python_cmd" -m pip --python "$venv_dir" install --editable "$root_dir"; then
        printf 'Fehler: RefCalendar konnte nicht in .venv installiert werden.\n' >&2
        return 1
    fi

    return 0
}

if ! _REFCALENDAR_SETUP_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"; then
    printf 'Fehler: Projektordner konnte nicht ermittelt werden.\n' >&2
    return 1
fi

if ! _refcalendar_private_setup "$_REFCALENDAR_SETUP_ROOT"; then
    unset -f _refcalendar_private_setup
    unset _REFCALENDAR_SETUP_ROOT
    return 1
fi

if ! source "$_REFCALENDAR_SETUP_ROOT/.venv/bin/activate"; then
    printf 'Fehler: .venv wurde installiert, konnte aber nicht aktiviert werden.\n' >&2
    unset -f _refcalendar_private_setup
    unset _REFCALENDAR_SETUP_ROOT
    return 1
fi

printf '.venv ist jetzt in dieser Shell aktiviert. Zum Verlassen "deactivate" ausführen.\n'
printf 'Tests startest du mit:\n'
printf '  python -m unittest discover -s python/tests -t python -p "test_*.py" -v\n'

unset -f _refcalendar_private_setup
unset _REFCALENDAR_SETUP_ROOT
