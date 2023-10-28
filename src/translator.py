"""Translates scraped maxroll data to a format that can be used by D4Companion."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from thefuzz import fuzz

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)

# TODO: Resolve in cleaner.py or find correct stat IDs
SKIP_STATS = [
    "Damage to Core skills",  # general core skill property
    "damage per second",  # general item property
    "high weapon damage",  # general item property
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
        with (Path("data") / "aspect_map.json").open("r") as f:
            self.aspect_map = json.load(f)

        with (Path("data") / "affix_map.json").open("r") as f:
            self.affix_map = json.load(f)

        with (Path("data") / "uniques.json").open("r") as f:
            self.uniques = json.load(f)

    def clean_plaintext(self, plaintext: str) -> str:
        """Clean a plaintext stat."""
        # Compile regular expressions
        pattern1 = re.compile(r"[^a-z\s]")  # remove non-alphabetic characters
        pattern2 = re.compile(r"\(.*?\)")  # remove parentheses and their contents
        pattern3 = re.compile(
            r"damage to (.+) enemies",
        )  # replace "damage to X enemies" with "X damage"
        pattern4 = re.compile(r"\b(the|passive)\b")  # remove "the" and "passive"

        # Preprocess uniques
        self.uniques = [unique.strip().lower() for unique in self.uniques]

        # Apply regular expressions
        cleaned = pattern1.sub("", plaintext.strip().lower())
        cleaned = pattern2.sub("", cleaned)
        cleaned = pattern3.sub(r"\1 damage", cleaned)

        # Remove unique items
        cleaned = " ".join(word for word in cleaned.split() if word not in self.uniques)

        # Replace specific words
        cleaned = pattern4.sub("", cleaned)
        cleaned = cleaned.replace("maximum life", "life")

        return cleaned.strip().lower()

    def map_plaintext_to_id(
        self: Translator,
        plaintext: str,
        map_to_use: dict[str, str],
    ) -> str:
        """Map a plaintext stat or aspect to an ID."""
        # check for exact matches
        for item, src_plaintext in map_to_use.items():
            if self.clean_plaintext(src_plaintext) == self.clean_plaintext(plaintext):
                return item

        # check for fuzzy matches
        best_match_id = None
        best_match_ratio = None
        for item, src_plaintext in map_to_use.items():
            ratio = fuzz.token_sort_ratio(
                self.clean_plaintext(src_plaintext),
                self.clean_plaintext(plaintext),
            )

            if not best_match_ratio or ratio > best_match_ratio:
                best_match_ratio = ratio
                best_match_id = item

        if best_match_ratio and best_match_ratio > 60:
            assert best_match_id is not None

            if best_match_ratio < 80:
                print(
                    f"Warning: used low fidelity fuzzy match: {best_match_ratio}% {plaintext!r} -> {map_to_use[best_match_id]!r}",
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
        """Translate a build from the scraped format to the D4Companion format."""
        rows = iter(data)
        _header = next(rows)

        output = {
            "Name": build_name,
            "ItemAffixes": [],
            "ItemAspects": [],  # TODO: Add aspects to translated builds
        }

        print(f"FILE: {build_name}.json")
        for gear_type, aspects, stat_numbered_list in rows:
            stats = {}

            # parse aspects
            for stat_numbered in stat_numbered_list.splitlines():
                re_match = re.search(
                    r"^[\d/\.\s]*\d[\d/\.\s]*[\.:]\s*(.*?)\s*(?:\(as\s*needed\))?(?:\(if\s*necessary\))?\s*$",
                    stat_numbered.lower(),
                )
                if not re_match:
                    continue

                stat = re_match[1]

                # skip stats that create errors
                if any(
                    self.clean_plaintext(stat) == self.clean_plaintext(skip_stat)
                    for skip_stat in SKIP_STATS
                ):
                    continue

                # map general resistance stats to all 5 resistances
                if self.clean_plaintext(stat) in {
                    self.clean_plaintext("any resistance").strip().lower(),
                    self.clean_plaintext("resists").strip().lower(),
                    self.clean_plaintext("single resistance").strip().lower(),
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
                # split multi-stats
                multi_stats = stat.split("/" if "/" in stat else ",")
                for multi_stat in multi_stats:
                    if is_resistance and not multi_stat.endswith("resistance"):
                        multi_stat += " resistance"

                    stats.setdefault(multi_stat, None)

            for stat in stats:
                output["ItemAffixes"].append(
                    {
                        "Id": self.map_plaintext_to_id(stat, self.affix_map),
                        "Type": gear_type,
                    },
                )

            # for aspect in aspects.splitlines():
            #     output["ItemAspects"].append(
            #         {
            #             "Id": self.map_plaintext_to_id(aspect, self.aspect_map),
            #             "Type": gear_type,
            #         },
            #     )

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
