"""Cleaner for the data files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


class Cleaner:
    def __init__(self: Cleaner) -> None:
        self.builds_dir = Path("data/builds")

    def run(self: Cleaner) -> None:
        """Clean build data files (remove empty builds)."""
        for file in self.builds_dir.iterdir():
            if file.is_file():
                with file.open() as f:
                    data = json.load(f)
                if not data:
                    logging.warning("Empty build file: %s", file.name)
        logging.info("All files checked.")
