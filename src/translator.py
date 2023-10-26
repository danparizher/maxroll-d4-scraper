"""Translates scraped maxroll data to a format that can be used by D4Companion."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


class Translator:
    def __init__(self: Translator) -> None:
        self.url = "https://raw.githubusercontent.com/josdemmers/Diablo4Companion/master/D4Companion/Data/Affixes.enUS.json"

    def create_map(self: Translator) -> dict[str, str] | None:
        """Return the map for IdName:Description."""
        response = requests.get(self.url, timeout=10)
        if response.status_code != 200:
            logging.error(
                "Failed to get data from %s. Status code: %s",
                self.url,
                response.status_code,
            )
            return None

        data = json.loads(response.content)
        return {item["IdName"]: item["Description"] for item in data}

    def compile_json(self: Translator) -> None:
        """Build the JSON file."""
        data = self.create_map()
        if data is not None:
            with Path("data\\stat_map.json").open("w") as f:
                data = dict(sorted(data.items(), key=lambda item: item[0]))
                json.dump(data, f, indent=2)

    def run(self: Translator) -> None:
        """Run the translator."""
        self.compile_json()


if __name__ == "__main__":
    translator = Translator()
    translator.run()
