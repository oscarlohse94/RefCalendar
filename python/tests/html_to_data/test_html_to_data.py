import unittest

from html_to_data import parse_games


def _game_html(
    observer_rows: str = "",
    referee_rows: str | None = None,
    venue_html: str = "Sporthalle<br>Beispielstraße 1",
) -> str:
    if referee_rows is None:
        referee_rows = """
          <tr><td>SR1</td><td>Schiedsrichter Eins</td></tr>
          <tr><td>Tel.</td><td>+49 111</td></tr>
          <tr><td>Mobil</td><td>+49 112</td></tr>
          <tr><td>E-Mail</td><td>sr1@example.test</td></tr>
          <tr><td>SR2</td><td>Schiedsrichter Zwei</td></tr>
          <tr><td>Tel.</td><td>+49 221</td></tr>
          <tr><td>Mobil</td><td>+49 222</td></tr>
          <tr><td>E-Mail</td><td>sr2@example.test</td></tr>
        """

    return f"""
    <div class="accordion-item">
      <div class="accordion-body">
        <table>
          <tr><td>Liga</td><td>Testliga</td></tr>
          <tr><td>Spielnr.</td><td>424242</td></tr>
          <tr><td>Datum | Zeit</td><td>17.11.2026 18:30</td></tr>
          <tr><td>Heim</td><td>Heimteam</td></tr>
          <tr><td>Gast</td><td>Gastteam</td></tr>
          <tr><td>FG</td><td>Fahrgemeinschaft</td></tr>
          {referee_rows}
          {observer_rows}
          <tr><td>VO</td><td>{venue_html}</td></tr>
        </table>
      </div>
    </div>
    """


class ParseGamesTests(unittest.TestCase):
    def test_parses_game_and_optional_observer(self) -> None:
        observer_rows = """
          <tr><td>BEO</td><td>Beobachter</td></tr>
          <tr><td>Tel.</td><td>+49 331</td></tr>
          <tr><td>Mobil</td><td>+49 332</td></tr>
          <tr><td>E-Mail</td><td>observer@example.test</td></tr>
        """

        [game] = parse_games(_game_html(observer_rows))

        self.assertEqual(game.game_id, 424242)
        self.assertEqual(game.date, "17.11.2026")
        self.assertEqual(game.time, "18:30")
        self.assertEqual(game.location, "Sporthalle\nBeispielstraße 1")
        self.assertEqual(game.referee[0].role, "SR1")
        self.assertEqual(game.referee[0].phone, "+49 111")
        self.assertEqual(game.referee[0].mobile, "+49 112")
        self.assertEqual(game.referee[0].mail, "sr1@example.test")
        self.assertEqual(game.referee[1].role, "SR2")
        self.assertEqual(game.referee[2].role, "OBSERVER")

    def test_observer_can_be_absent(self) -> None:
        [game] = parse_games(_game_html())

        self.assertIsNone(game.referee[2])

    def test_referee_slots_can_both_be_absent(self) -> None:
        [game] = parse_games(_game_html(referee_rows=""))

        self.assertEqual(game.referee, (None, None, None))

    def test_one_referee_slot_can_be_absent(self) -> None:
        referee_rows = "<tr><td>SR1</td><td>Schiedsrichter Eins</td></tr>"

        [game] = parse_games(_game_html(referee_rows=referee_rows))

        self.assertEqual(game.referee[0].role, "SR1")
        self.assertIsNone(game.referee[1])

    def test_location_drops_what3words_marker_and_suffix(self) -> None:
        venue_html = (
            "DSD Düsseldorf Sportanlage<br>"
            "Altenbergstr. 81<br>"
            "40235 Düsseldorf<br>"
            "Deutschland<br>"
            "///alpha.bravo.charlie"
        )

        [game] = parse_games(_game_html(venue_html=venue_html))

        self.assertEqual(
            game.location,
            "DSD Düsseldorf Sportanlage\n"
            "Altenbergstr. 81\n"
            "40235 Düsseldorf\n"
            "Deutschland",
        )


if __name__ == "__main__":
    unittest.main()
