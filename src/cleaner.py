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
        self.builds_dir = Path("data/builds")
        with Path("data/uniques.json").open() as f:
            self.uniques = json.load(f)
        self.equipment_types = [
            "helm",
            "chest",
            "gloves",
            "pants",
            "boots",
            "weapon",
            "ranged",
            "offhand",
            "amulet",
            "ring",
        ]

    def remove_unique_items(self: Cleaner) -> None:
        """Remove unique and best-in-slot items from equipment."""
        for file in self.builds_dir.iterdir():
            if file.is_file():
                with file.open() as f:
                    data = json.load(f)
                # Skip the first row (header)
                new_data = [data[0]]  # Keep the header in the new data
                for row in data[1:]:
                    if (
                        len(row) > 1
                        and "unique" not in row[0].lower()
                        and not re.search(r"best[-\s]in[-\s]slot", row[0].lower())
                    ):
                        for unique in self.uniques:
                            row[2] = row[2].replace(f"(with {unique})", "")
                        new_data.append(row)
                with file.open("w") as f:
                    json.dump(new_data, f, indent=2)
        logging.info("All files cleaned.")

    def replace_valid_equipment(self: Cleaner) -> None:
        """Replace equipment types with a standardized name according to the closest match."""
        for file in self.builds_dir.iterdir():
            if file.is_file():
                with file.open() as f:
                    data = json.load(f)
                for row in data:
                    if row:
                        equipment_type = row[0]
                        for valid_equipment in self.equipment_types:
                            if valid_equipment.lower() in equipment_type.lower():
                                row[0] = valid_equipment
                                break
                with file.open("w") as f:
                    json.dump(data, f, indent=2)
        logging.info("Equipment names standardized.")

    def run(self: Cleaner) -> None:
        self.remove_unique_items()
        self.replace_valid_equipment()


if __name__ == "__main__":
    cleaner = Cleaner()
    cleaner.run()
