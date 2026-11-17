from dataclasses import dataclass, field


@dataclass
class Referee:
    """Represents a referee."""

    role: str
    name: str
    mail: str | None = None
    phone: str | None = None
    mobile: str | None = None

@dataclass
class Game:
    """Represent a game for the referee."""

    game_id: int
    league: str
    date: str
    time: str
    home_team: str
    away_team: str
    location: str
    referee: tuple[Referee | None, Referee | None, Referee | None]

@dataclass
class User:
    """Represents a user of this tool."""

    link: str
    google_calendar: str
    games: list[Game] = field(default_factory=list)
