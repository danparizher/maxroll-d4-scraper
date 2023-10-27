"""Translates scraped maxroll data to a format that can be used by D4Companion."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import requests
from thefuzz import fuzz

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)

# TODO: Resolve in cleaner.py or find correct stat IDs
SKIP_STATS = [
    "Damage to Core skills",  # general core skill property
    "High Damage per Second",  # general item property
    "Any",  # placeholder - should be cleaned
    "Movement Speed for 4 Seconds After Killing an Elite",  # unclear??? (no associated ID in stat map)
    "movement speed after killing an elite",  # same ^ (no associated ID in stat map)
    "movement speed on elite kill",  # same ^ (no associated ID in stat map)
    "After using Teleport, Close enemies are Pulled to you and Stunned for 2-3 Seconds, but Teleport's Cooldown is increased by 20%",  # unique
    "Maximum Fury (with Ramaladni's Magnum Opus)",  # another unique item ^^
    "PH",  # same ^
    "Lucky Hit: Chance to empower all of your Minions, causing the next attack from each to explode for Physical Damage",  # unique
]


class Translator:
    def __init__(self: Translator) -> None:
        self.url = "https://raw.githubusercontent.com/josdemmers/Diablo4Companion/master/D4Companion/Data/Affixes.enUS.json"
        self.stat_map = self.create_map()

        with Path("data\\stat_map.json").open("w") as f:
            json.dump(self.stat_map, f, indent=2)

    def create_map(self: Translator) -> dict[str, str]:
        """Return the map for IdName:Description."""
        response = requests.get(self.url, timeout=10)
        if response.status_code != 200:
            msg = f"Failed to get data from {self.url}. Status code: {response.status_code}"
            raise requests.exceptions.HTTPError(msg)

        data = json.loads(response.content)
        return {
            item["IdName"]: item["Description"]
            for item in sorted(data, key=lambda item: item["IdName"])
        }

    @staticmethod
    def clean_plaintext(plaintext: str) -> str:
        cleaned = re.sub(r"[^a-z\s]", "", plaintext.strip().lower())
        cleaned = cleaned.replace("ranks to", "ranks of the")
        cleaned = re.sub(r"damage to (.+) enemies", r"\1 damage", cleaned)
        return cleaned.replace("maximum life", "life")

    def map_plaintext_to_id(self: Translator, plaintext: str) -> str:
        # check for exact matches
        for stat_id, src_plaintext in self.stat_map.items():
            if self.clean_plaintext(src_plaintext) == self.clean_plaintext(plaintext):
                return stat_id

        # check for fuzzy matches
        best_match_id = None
        best_match_ratio = None
        for stat_id, src_plaintext in self.stat_map.items():
            ratio = fuzz.token_sort_ratio(
                self.clean_plaintext(src_plaintext),
                self.clean_plaintext(plaintext),
            )

            if not best_match_ratio or ratio > best_match_ratio:
                best_match_ratio = ratio
                best_match_id = stat_id

        if best_match_ratio and best_match_ratio > 60:
            assert best_match_id is not None

            if best_match_ratio < 80:
                print(
                    f"Warning: used low fidelity fuzzy match: {best_match_ratio}% {plaintext!r} -> {self.stat_map[best_match_id]!r}",
                )

            return best_match_id

        # no matches - cry
        msg = f"Failed to find a match for {plaintext} - fuzzy matched {best_match_id} with ratio {best_match_ratio}%"
        raise Exception(msg)  # noqa

    def translate(
        self: Translator,
        build_name: str,
        data: list[list[str]],
    ) -> dict[str, Any]:
        rows = iter(data)
        _header = next(rows)

        output = {
            "Name": build_name,
            "ItemAffixes": [],
            "ItemAspects": [],
        }

        print(f"FILE: {build_name}json")
        for gear_type, _aspects, stat_numbered_list in rows:
            stats = {}

            for stat_numbered in stat_numbered_list.splitlines():
                re_match = re.search(
                    r"^[\d/\.\s]*\d[\d/\.\s]*[\.:]\s*(.*?)\s*(?:\(as\s*needed\))?(?:\(if\s*necessary\))?\s*$",
                    stat_numbered.lower(),
                )
                if not re_match:
                    continue

                stat = re_match[1]

                if any(
                    self.clean_plaintext(stat) == self.clean_plaintext(skip_stat)
                    for skip_stat in SKIP_STATS
                ):
                    continue

                if self.clean_plaintext(stat) in {
                    self.clean_plaintext("any resistance"),
                    self.clean_plaintext("resists"),
                    self.clean_plaintext("single resistance"),
                }:
                    stat = "fire / cold / lightning / poison / shadow resistance"

                is_resistance = (
                    stat.endswith("resistance")
                    or sum(
                        r in stat
                        for r in ("fire", "cold", "lightning", "poison", "shadow")
                    )
                    >= 3
                )
                multi_stats = stat.split("/" if "/" in stat else ",")
                for multi_stat in multi_stats:
                    if is_resistance and not multi_stat.endswith("resistance"):
                        multi_stat += " resistance"

                    stats.setdefault(multi_stat, None)

            for stat in stats:
                output["ItemAffixes"].append(
                    {
                        "Id": self.map_plaintext_to_id(stat),
                        "Type": gear_type,
                    },
                )

        return output

    def run(self: Translator) -> None:
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
