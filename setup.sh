#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'Bitte in der aktuellen Bash-Shell mit "source ./setup.sh" starten.\n' >&2
    exit 1
fi

_refcalendar_private_setup() {
    local root_dir="$1"
    local venv_dir="$root_dir/.venv"
    local pip_help=""
    local python_cmd=""

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
