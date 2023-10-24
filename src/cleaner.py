"""Cleaner for the data files."""

import json
import logging
import re
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


def remove_constant_items() -> None:
    """Remove unique and best-in-slot items, as they are not relevant to the stat priorities."""
    builds_dir = Path("data\\builds")
    for file in builds_dir.iterdir():
        if file.is_file():
            with file.open() as f:
                data = json.load(f)
            new_data = [
                row
                for row in data
                if (
                    "unique" not in row[0].lower()
                    and not re.search(r"best[-\s]in[-\s]slot", row[0].lower())
                )
            ]
            with file.open("w") as f:
                json.dump(new_data, f, indent=2)
    logging.info("All files cleaned.")


def run() -> None:
    """Run the cleaner."""
    remove_constant_items()


if __name__ == "__main__":
    run()
