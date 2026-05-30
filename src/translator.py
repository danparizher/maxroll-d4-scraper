"""Translates scraped maxroll data to a format that can be used by D4Companion."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)

AFFIXES_URL = "https://raw.githubusercontent.com/josdemmers/Diablo4Companion/master/D4Companion/Data/Affixes.enUS.json"


def _build_nid_to_idname_map() -> dict[str, str]:
    """Build a mapping from numeric affix SNO IDs to their IdName."""
    response = requests.get(AFFIXES_URL, timeout=10)
    affixes = json.loads(response.content)
    nid_map: dict[str, str] = {}
    for affix in affixes:
        id_name = affix.get("IdName", "").split(";")[0]
        for sno in affix.get("IdSnoList", []):
            nid_map[str(sno)] = id_name
    return nid_map


class Translator:
    def __init__(self: Translator) -> None:
        with (Path("data") / "aspect_map.json").open("r") as f:
            self.aspect_map = json.load(f)

        with (Path("data") / "affix_map.json").open("r") as f:
            self.affix_map = json.load(f)

        with (Path("data") / "uniques.json").open("r") as f:
            self.uniques = json.load(f)

        self.nid_map = _build_nid_to_idname_map()

    def translate(
        self: Translator,
        build_name: str,
        data: list[list[Any]],
    ) -> dict[str, Any]:
        """Translate a build from the scraped format to the D4Companion format."""
        if not data:
            logging.error("No data found for build: %s", build_name)
            return {}

        output: dict[str, str | list[dict[str, str]]] = {
            "Name": build_name,
            "ItemAffixes": [],
            "ItemAspects": [],
        }

        logging.info("Translating: %s", build_name)
        for row in data:
            if len(row) < 3:
                continue

            gear_type, aspects, affix_text = row

            # Parse aspects (already IDs from the planner)
            if isinstance(aspects, list):
                for aspect_id in aspects:
                    if aspect_id and isinstance(output["ItemAspects"], list):
                        output["ItemAspects"].append(
                            {
                                "Id": aspect_id,
                                "Type": gear_type,
                            },
                        )

            # Parse affix NIDs
            if isinstance(affix_text, str):
                for line in affix_text.splitlines():
                    nid_match = re.search(r"nid:(\d+)", line)
                    if nid_match:
                        nid = nid_match.group(1)
                        id_name = self.nid_map.get(nid)
                        if id_name and isinstance(output["ItemAffixes"], list):
                            output["ItemAffixes"].append(
                                {
                                    "Id": id_name,
                                    "Type": gear_type,
                                },
                            )
                        elif not id_name:
                            logging.debug("Unknown affix NID %s in %s", nid, build_name)

        return output

    def run(self: Translator) -> None:
        """Translate all scraped builds to the D4Companion format."""
        translated_builds_dir = Path("data") / "translated_builds"

        translated_builds_dir.mkdir(exist_ok=True)
        for tb in translated_builds_dir.iterdir():
            tb.unlink()

        for build_file in (Path("data") / "builds").iterdir():
            with build_file.open("r") as f:
                translated_build = self.translate(build_file.name[:-5], json.load(f))

            with (translated_builds_dir / build_file.name).open("w") as f:
                json.dump(translated_build, f, indent=2)


if __name__ == "__main__":
    Translator().run()
