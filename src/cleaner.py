"""Cleaner for the data files."""

from __future__ import annotations
import json
import logging
import re
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


class Cleaner:
    def __init__(self: Cleaner) -> None:
        self.builds_dir = Path("data\\builds")

    def remove_constant_items(self) -> None:
        for file in self.builds_dir.iterdir():
            if file.is_file():
                with file.open() as f:
                    data = json.load(f)
                new_data = [
                    row
                    for row in data
                    if (
                        len(row) > 0
                        and "unique" not in row[0].lower()
                        and not re.search(r"best[-\s]in[-\s]slot", row[0].lower())
                    )
                ]
                with file.open("w") as f:
                    json.dump(new_data, f, indent=2)
        logging.info("All files cleaned.")

    def remove_optional(self: Cleaner) -> None:
        for file in self.builds_dir.iterdir():
            if file.is_file():
                with file.open() as f:
                    data = json.load(f)
                new_data = [
                    [re.sub(r"\(Optional\)", "", stat, flags=re.I) for stat in row]
                    for row in data
                ]
                with file.open("w") as f:
                    json.dump(new_data, f, indent=2)

    def run(self: Cleaner) -> None:
        self.remove_constant_items()
        self.remove_optional()


if __name__ == "__main__":
    cleaner = Cleaner()
    cleaner.run()
