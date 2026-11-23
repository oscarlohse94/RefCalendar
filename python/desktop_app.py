# Copyright (c) 2026 Oscar Lohse

"""Initial Tkinter desktop interface for RefCalendar."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from env_handler import (
    get_dhb_url,
    get_referee_name,
    load_environment,
    validate_dhb_url,
)
from env_handler import (
    set_dhb_url as persist_dhb_url,
)
from env_handler import (
    set_referee_name as persist_referee_name,
)
from game_to_json import games_to_google_calendar_events
from get_games import fetch_html
from html_to_data import parse_user
from json_to_google import sync_google_calendar_events
from user_cache import UserCacheError, load_user_cache, save_user_cache

if TYPE_CHECKING:
    from game_data import Game, User


@dataclass(frozen=True)
class _SyncSuccess:
    user: User
    source_url: str
    created: int
    updated: int
    cache_error: str | None


@dataclass(frozen=True)
class _SyncFailure:
    message: str
    user: User | None
    source_url: str


class RefCalendarWindow:
    """Render the first desktop UI draft."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the application window and load its cached user."""
        self.root = root
        self.user: User | None = None
        self._sync_results: Queue[_SyncSuccess | _SyncFailure] = Queue()
        load_environment()
        referee_name = get_referee_name()
        try:
            dhb_url = get_dhb_url()
        except RuntimeError:
            dhb_url = ""
        self.link_var = tk.StringVar(value=dhb_url)
        self.show_link_var = tk.BooleanVar(value=False)
        self._build_window(root, referee_name, dhb_url)
        self._load_cached_user(dhb_url)

    def _build_window(self, root: tk.Tk, referee_name: str, dhb_url: str) -> None:
        """Build the window layout."""
        root.title("RefCalendar")
        root.geometry("1000x720")
        root.minsize(820, 560)
        root.resizable(width=True, height=True)
        container = ttk.Frame(root, padding=24)
        container.pack(fill="both", expand=True)
        self._build_header(container, referee_name)
        self._build_link_section(container)
        self._build_status_section(container, referee_name, dhb_url)
        self._build_games_section(container)
        self._build_actions(container)

    def _build_header(self, container: ttk.Frame, referee_name: str) -> None:
        """Build the greeting and introductory text."""
        greeting = f"Hallo, {referee_name}!" if referee_name else "Hallo!"
        self.greeting_var = tk.StringVar(value=greeting)
        ttk.Label(
            container,
            textvariable=self.greeting_var,
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="Verwalte hier deine DHB- und Google-Kalender-Verknüpfung.",
        ).pack(anchor="w", pady=(4, 20))

    def _build_link_section(self, container: ttk.Frame) -> None:
        """Build the DHB link controls."""
        link_frame = ttk.LabelFrame(
            container,
            text="Persönlicher DHB-Link",
            padding=14,
        )
        link_frame.pack(fill="x")

        self.link_entry = ttk.Entry(
            link_frame,
            textvariable=self.link_var,
            show="*",
        )
        self.link_entry.pack(fill="x")

        ttk.Checkbutton(
            link_frame,
            text="Link anzeigen",
            variable=self.show_link_var,
            command=self._toggle_link_visibility,
        ).pack(anchor="w", pady=(6, 10))
        ttk.Button(link_frame, text="Set Link", command=self.set_dhb_url).pack(anchor="e")

    def _build_status_section(
        self,
        container: ttk.Frame,
        referee_name: str,
        dhb_url: str,
    ) -> None:
        """Build the referee, calendar, and sync status section."""
        status_frame = ttk.LabelFrame(container, text="Status", padding=14)
        status_frame.pack(fill="x", pady=(16, 0))
        referee_status = referee_name or "Noch nicht eingerichtet"
        self.referee_status = tk.StringVar(value=referee_status)
        self.link_status = tk.StringVar(
            value="DHB-Link ist hinterlegt"
            if dhb_url
            else "Kein gültiger DHB-Link hinterlegt",
        )
        ttk.Label(status_frame, textvariable=self.referee_status).pack(anchor="w")
        ttk.Label(status_frame, textvariable=self.link_status).pack(anchor="w", pady=(6, 0))
        self.google_status = tk.StringVar(value="Google-Konto: Noch nicht verbunden")
        ttk.Label(status_frame, textvariable=self.google_status).pack(anchor="w", pady=(6, 0))
        self.sync_status = tk.StringVar(value="Noch keine")
        ttk.Label(status_frame, textvariable=self.sync_status).pack(anchor="w", pady=(6, 0))

    def _build_games_section(self, container: ttk.Frame) -> None:
        """Build the current games table and its scrollbars."""
        games_frame = ttk.LabelFrame(container, text="Aktuelle Spiele", padding=10)
        games_frame.pack(fill="both", expand=True, pady=(16, 0))
        self.games_status = tk.StringVar(value="Noch keine gespeicherten Spiele")
        ttk.Label(games_frame, textvariable=self.games_status).pack(anchor="w", pady=(0, 8))
        table_frame = ttk.Frame(games_frame)
        table_frame.pack(fill="both", expand=True)
        columns = ("date", "time", "league", "home", "away", "location")
        self.games_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=8,
        )
        headings = {
            "date": ("Datum", 95),
            "time": ("Uhrzeit", 75),
            "league": ("Liga", 100),
            "home": ("Heim", 150),
            "away": ("Gast", 150),
            "location": ("Spielort", 260),
        }
        for column, (heading, width) in headings.items():
            self.games_tree.heading(column, text=heading)
            self.games_tree.column(column, width=width, minwidth=70, anchor="w")

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.games_tree.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.games_tree.xview,
        )
        self.games_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        self.games_tree.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

    def _build_actions(self, container: ttk.Frame) -> None:
        """Build sync and future-feature controls."""
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(18, 0))
        self.sync_button = ttk.Button(
            actions,
            text="Sync with Google",
            command=self._sync_with_google,
            state="disabled",
        )
        self.sync_button.pack(side="left")
        ttk.Button(
            actions,
            text="DeSync Google",
            state="disabled",
        ).pack(side="left", padx=(8, 0))

        self.autostart_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            container,
            text="Autostart aktiv",
            variable=self.autostart_var,
            state="disabled",
        ).pack(anchor="w", pady=(16, 0))

        ttk.Label(
            container,
            text="Entwurf: Google-Kontoverwaltung und Autostart folgen.",
            wraplength=500,
        ).pack(anchor="w", pady=(14, 0))

    def _toggle_link_visibility(self) -> None:
        self.link_entry.configure(show="" if self.show_link_var.get() else "*")

    def _display_games(self, games: list[Game]) -> None:
        for item in self.games_tree.get_children():
            self.games_tree.delete(item)

        for game in games:
            self.games_tree.insert(
                "",
                "end",
                iid=str(game.game_id),
                values=(
                    game.date,
                    game.time,
                    game.league,
                    game.home_team,
                    game.away_team,
                    game.location.replace("\n", ", "),
                ),
            )

        self.games_status.set(f"{len(games)} Spiele geladen")

    def _sync_with_google(self) -> None:
        if self.user is None:
            messagebox.showwarning(
                "Keine Spiele geladen",
                "Speichere zuerst deinen DHB-Link, damit die Spiele geladen werden.",
                parent=self.root,
            )
            return

        try:
            source_url = get_dhb_url()
        except RuntimeError as exc:
            messagebox.showerror(
                "DHB-Link fehlt",
                str(exc),
                parent=self.root,
            )
            return

        self.sync_button.configure(state="disabled")
        self.sync_status.set("Daten werden aktualisiert und synchronisiert …")
        Thread(
            target=self._sync_worker,
            args=(source_url,),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_sync_results)

    def _sync_worker(self, source_url: str) -> None:
        user = None
        try:
            user = parse_user(fetch_html(source_url))
            cache_error = None
            try:
                save_user_cache(user, source_url)
            except UserCacheError as exc:
                cache_error = str(exc)
            persist_referee_name(user.name)
            calendar_events = games_to_google_calendar_events(user.games)
            created, updated = sync_google_calendar_events(
                calendar_events,
                open_browser=True,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            self._sync_results.put(
                _SyncFailure(
                    message=str(exc),
                    user=user,
                    source_url=source_url,
                ),
            )
        else:
            self._sync_results.put(
                _SyncSuccess(
                    user=user,
                    source_url=source_url,
                    created=created,
                    updated=updated,
                    cache_error=cache_error,
                ),
            )

    def _poll_sync_results(self) -> None:
        try:
            result = self._sync_results.get_nowait()
        except Empty:
            self.root.after(100, self._poll_sync_results)
            return

        self.sync_button.configure(state="normal")
        if isinstance(result, _SyncFailure):
            if result.user is not None:
                self._apply_user(result.user, result.source_url)
            self.sync_status.set("Synchronisierung fehlgeschlagen")
            messagebox.showerror(
                "Synchronisierung fehlgeschlagen",
                result.message,
                parent=self.root,
            )
            return

        self._apply_user(result.user, result.source_url)
        self.google_status.set("Google-Konto: Verbunden")
        synced_at = datetime.now().astimezone().strftime("%d.%m.%Y %H:%M")
        self.sync_status.set(f"{result.created} erstellt, {result.updated} aktualisiert ({synced_at})")
        message = (
            f"{result.created} Termine erstellt und "
            f"{result.updated} Termine aktualisiert."
        )
        if result.cache_error:
            message += f"\n\nDie Spiele konnten nicht zwischengespeichert werden: {result.cache_error}"
            messagebox.showwarning(
                "Synchronisiert, Cache nicht gespeichert",
                message,
                parent=self.root,
            )
        else:
            messagebox.showinfo(
                "Google Calendar synchronisiert",
                message,
                parent=self.root,
            )

    def _apply_user(self, user: User, source_url: str) -> None:
        self.user = user
        self.link_var.set(source_url)
        self.link_status.set("DHB-Link gespeichert")
        self.greeting_var.set(f"Hallo, {user.name}!")
        self.referee_status.set(user.name)
        self._display_games(user.games)

    def _load_cached_user(self, source_url: str) -> None:
        if not source_url:
            return

        try:
            cached_user = load_user_cache(source_url)
        except UserCacheError as exc:
            self.games_status.set("Gespeicherte Spiele konnten nicht geladen werden")
            messagebox.showwarning(
                "Spiel-Cache nicht verfügbar",
                str(exc),
                parent=self.root,
            )
            return
        if cached_user is None:
            return

        self.user = cached_user.user
        self._display_games(self.user.games)
        self.greeting_var.set(f"Hallo, {self.user.name}!")
        self.referee_status.set(self.user.name)
        self.sync_button.configure(state="normal")
        fetched_at = cached_user.fetched_at.astimezone().strftime("%d.%m.%Y %H:%M")
        self.games_status.set(f"{len(self.user.games)} gespeicherte Spiele; zuletzt geladen: {fetched_at}")

    def set_dhb_url(self) -> None:
        """Fetch and save the user's DHB profile URL and referee data."""
        try:
            dhb_url = validate_dhb_url(self.link_var.get())
            user = parse_user(fetch_html(dhb_url))
            persist_dhb_url(dhb_url)
            persist_referee_name(user.name)
        except ValueError as exc:
            messagebox.showerror(
                "Ungültiger Link",
                str(exc),
                parent=self.root,
            )
            return
        except (OSError, RuntimeError) as exc:
            messagebox.showerror(
                "DHB-Verbindung fehlgeschlagen",
                str(exc),
                parent=self.root,
            )
            return

        self.link_var.set(dhb_url)
        self._apply_user(user, dhb_url)
        self.sync_button.configure(state="normal")
        try:
            save_user_cache(user, dhb_url)
        except UserCacheError as exc:
            self.games_status.set(f"{len(user.games)} Spiele geladen; Cache konnte nicht gespeichert werden")
            messagebox.showwarning(
                "Spiel-Cache konnte nicht gespeichert werden",
                str(exc),
                parent=self.root,
            )
            return
        messagebox.showinfo(
            "Link gespeichert",
            f"Der DHB-Link wurde gespeichert. Erkannter Name: {user.name}\n"
            f"{len(user.games)} Spiele wurden lokal zwischengespeichert.",
            parent=self.root,
        )


def run() -> None:
    """Open the RefCalendar desktop window."""
    root = tk.Tk()
    RefCalendarWindow(root)
    root.mainloop()


if __name__ == "__main__":
    run()
