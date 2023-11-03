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

    @staticmethod
    def clean_aspect(plaintext: str) -> str:
        """Clean a plaintext aspect."""
        pattern1 = re.compile(r"^.*:")
        pattern2 = re.compile(
            r"\b(aspect)\b",
        )  # remove "aspect"

        cleaned = pattern1.sub("", plaintext.strip().lower())
        cleaned = pattern2.sub("", cleaned)

        return cleaned.strip().lower()

    def clean_affix(self, plaintext: str) -> str:
        """Clean a plaintext affix."""
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

    def map_aspect_to_id(self: Translator, plaintext: str) -> str:
        """Map a plaintext stat to a stat ID."""
        # check for exact matches
        for aspect_id, src_plaintext in self.aspect_map.items():
            if self.clean_aspect(src_plaintext) == self.clean_aspect(plaintext):
                return aspect_id

        # check for fuzzy matches
        best_match_id = None
        best_match_ratio = None
        for aspect_id, src_plaintext in self.aspect_map.items():
            ratio = fuzz.token_sort_ratio(
                self.clean_aspect(src_plaintext),
                self.clean_aspect(plaintext),
            )

            if not best_match_ratio or ratio > best_match_ratio:
                best_match_ratio = ratio
                best_match_id = aspect_id

        if best_match_ratio and best_match_ratio > 55:
            assert best_match_id is not None

            if best_match_ratio < 80:
                print(
                    f"Warning: used low fidelity fuzzy match: {best_match_ratio}% {plaintext!r} -> {self.aspect_map[best_match_id]!r}",
                )

            return best_match_id

        # no matches - cry
        msg = f"Failed to find a match for {plaintext} - fuzzy matched {best_match_id} with ratio {best_match_ratio}%"
        raise Exception(msg)  # noqa

    def map_affix_to_id(self: Translator, plaintext: str) -> str:
        """Map a plaintext stat to a stat ID."""
        # check for exact matches
        for affix_id, src_plaintext in self.affix_map.items():
            if self.clean_affix(src_plaintext) == self.clean_affix(plaintext):
                return affix_id

        # check for fuzzy matches
        best_match_id = None
        best_match_ratio = None
        for affix_id, src_plaintext in self.affix_map.items():
            ratio = fuzz.token_sort_ratio(
                self.clean_affix(src_plaintext),
                self.clean_affix(plaintext),
            )

            if not best_match_ratio or ratio > best_match_ratio:
                best_match_ratio = ratio
                best_match_id = affix_id

        if best_match_ratio and best_match_ratio > 55:
            assert best_match_id is not None

            if best_match_ratio < 80:
                print(
                    f"Warning: used low fidelity fuzzy match: {best_match_ratio}% {plaintext!r} -> {self.affix_map[best_match_id]!r}",
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

        output: dict[str, str | list[dict[str, str]]] = {
            "Name": build_name,
            "ItemAffixes": [],
            "ItemAspects": [],
        }

        print(f"FILE: {build_name}.json")
        for gear_type, aspects, stat_numbered_list in rows:
            affixes: dict[str, None] = {}

            # parse aspects
            for aspect in aspects:
                cleaned_aspect = self.clean_aspect(aspect)
                aspect_id = self.map_aspect_to_id(cleaned_aspect)
                if isinstance(output["ItemAspects"], list):
                    output["ItemAspects"].append(
                        {
                            "Id": aspect_id,
                            "Type": gear_type,
                        },
                    )

            # parse affixes
            for stat_numbered in stat_numbered_list.splitlines():
                re_match = re.search(
                    r"^[\d/\.\s]*\d[\d/\.\s]*[\.:]\s*(.*?)\s*(?:\(as\s*needed\))?(?:\(if\s*necessary\))?\s*$",
                    stat_numbered.lower(),
                )
                if not re_match:
                    continue

                affix = re_match[1]

                # skip stats that create errors
                if any(
                    self.clean_affix(affix) == self.clean_affix(skip_stat)
                    for skip_stat in SKIP_STATS
                ):
                    continue

                # map general resistance stats to all 5 resistances
                if self.clean_affix(affix) in {
                    self.clean_affix("any resistance").strip().lower(),
                    self.clean_affix("resists").strip().lower(),
                    self.clean_affix("single resistance").strip().lower(),
                }:
                    affix = "fire / cold / lightning / poison / shadow resistance"

                is_resistance = (
                    affix.endswith("resistance")
                    or sum(
                        r in affix
                        for r in ("fire", "cold", "lightning", "poison", "shadow")
                    )
                    >= 3
                )
                # split multi-stats
                multi_stats = affix.split("/" if "/" in affix else ",")
                for multi_stat in multi_stats:
                    if is_resistance and not multi_stat.endswith("resistance"):
                        multi_stat += " resistance"

                    affixes.setdefault(multi_stat, None)

            for affix in affixes:
                if isinstance(output["ItemAffixes"], list):
                    output["ItemAffixes"].append(
                        {
                            "Id": self.map_affix_to_id(affix),
                            "Type": gear_type,
                        },
                    )

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
