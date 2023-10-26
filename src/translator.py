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

    def create_map(self: Translator) -> dict[str, str]:
        """Return the map for IdName:Description."""
        response = requests.get(self.url, timeout=10)
        data = json.loads(response.content)
        return {item["IdName"]: item["Description"] for item in data}

    def build_json(self: Translator) -> None:
        """Build the JSON file."""
        data = self.create_map()
        with Path("data\\map.json").open("w") as f:
            data = dict(sorted(data.items(), key=lambda item: item[0]))
            json.dump(data, f, indent=2)


def run() -> None:
    """Run the translator."""
    translator = Translator()
    translator.build_json()


if __name__ == "__main__":
    run()
