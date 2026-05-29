"""Retrieves the stat priorities from the website using the following process.

1. Generate a list of class paths (barbarian, druid, necromancer, rogue, sorcerer, etc.).
2. For each class path, retrieve the build paths for that class (whirlwind-barbarian, twisting-blades-rogue, etc.)
3. For each build path, retrieve the gear/affix data from the embedded planner profile.
4. Write the gear data to a JSON file in the builds directory.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import operator
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


class Uniques:
    def __init__(self: Uniques) -> None:
        self.core_toc: dict[str, dict[str, str]] = {}
        self.item_files: list[str] = []
        self.uniques: list[str] = []

    @staticmethod
    def fetch_data(url: str) -> dict[str, dict[str, str]]:
        """Return the JSON data from the given URL."""
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            msg = f"Failed to get data from {url}. Status code: {response.status_code}"
            raise RuntimeError(msg)
        return response.json()

    def fetch_item_files(self: Uniques) -> list[str] | None:
        """Return a list of item files."""
        url = "https://raw.githubusercontent.com/blizzhackers/d4data/master/json/base/CoreTOC.dat.json"
        self.core_toc = self.fetch_data(url)
        self.item_files = [
            name for name in self.core_toc["73"].values() if "unique" in name.lower()
        ]
        return self.item_files

    def get_uniques(self) -> list[str]:
        """Return a list of unique item names."""
        item_files = self.fetch_item_files()
        if item_files is not None:
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(
                        self.fetch_data,
                        f"https://raw.githubusercontent.com/blizzhackers/d4data/master/json/enUS_Text/meta/StringList/Item_{value}.stl.json",
                    )
                    for value in item_files
                ]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        data: dict[str, Any] = future.result()
                        self.uniques.append(data["arStrings"][0]["szText"])
                    except Exception as e:
                        logging.warning("Skipping unavailable unique item data: %s", e)
        return self.uniques

    def create_uniques(self: Uniques) -> None:
        """Create JSON file for the list of unique items."""
        data = self.get_uniques()
        with Path("data/uniques.json").open("w") as f:
            data.sort()
            json.dump(data, f, indent=2)


# TODO: use offical source (d4data)
class AspectMap:
    def __init__(self: AspectMap) -> None:
        self.url = "https://raw.githubusercontent.com/josdemmers/Diablo4Companion/master/D4Companion/Data/Aspects.enUS.json"
        self.aspect_map = self.create_map()

        with Path("data/aspect_map.json").open("w") as f:
            json.dump(self.aspect_map, f, indent=2)

    def create_map(self: AspectMap) -> dict[str, str]:
        """Return the map for IdName:Name."""
        response = requests.get(self.url, timeout=10)
        if response.status_code != 200:
            msg = f"Failed to get data from {self.url}. Status code: {response.status_code}"
            logging.error(msg)

        data = json.loads(response.content)
        return {
            item["IdName"]: item["Name"]
            for item in sorted(data, key=operator.itemgetter("IdName"))
        }


class AffixMap:
    def __init__(self: AffixMap) -> None:
        self.url = "https://raw.githubusercontent.com/josdemmers/Diablo4Companion/master/D4Companion/Data/Affixes.enUS.json"
        self.affix_map = self.create_map()

        with Path("data/affix_map.json").open("w") as f:
            json.dump(self.affix_map, f, indent=2)

    def create_map(self: AffixMap) -> dict[str, str]:
        """Return the map for IdName:Description."""
        response = requests.get(self.url, timeout=10)
        if response.status_code != 200:
            msg = f"Failed to get data from {self.url}. Status code: {response.status_code}"
            logging.error(msg)

        data = json.loads(response.content)
        return {
            item["IdName"]: item["Description"]
            for item in sorted(data, key=operator.itemgetter("IdName"))
        }


def generate_class_paths() -> list[str]:
    """Return a list of class paths."""
    root = "https://maxroll.gg/d4/build-guides?filter[metas][taxonomy]=taxonomies.metas&filter[metas][value]=d4-endgame&filter[classes][taxonomy]=taxonomies.classes&filter[classes][value]=d4-"
    classes = ["barbarian", "druid", "necromancer", "paladin", "rogue", "sorcerer", "spiritborn", "warlock"]
    return [root + c for c in classes]


def get_build_paths_for_class(path: str) -> list[str]:
    """Return a list of build paths for the given class path."""
    logging.info("Retrieving build paths from %s", path)
    response = requests.get(path, timeout=20)
    if response.status_code != 200:
        logging.error("Failed to get data from %s. Status code: %s", path, response.status_code)
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    build_paths = [
        f"https://maxroll.gg{a['href']}"
        for a in soup.find_all("a", href=True)
        if "/d4/build-guides/" in a["href"]
        and a["href"] != "/d4/build-guides/"
        and "guide" in a["href"]
    ]
    build_paths = list(dict.fromkeys(build_paths))  # deduplicate preserving order
    for build_path in build_paths:
        logging.info("Retrieved build path: %s", build_path)
    return build_paths


def get_all_build_paths() -> list[str]:
    """Return a list of all build paths."""
    all_build_paths = []
    class_paths = generate_class_paths()
    with ThreadPoolExecutor() as executor:
        future_to_path = {
            executor.submit(get_build_paths_for_class, path): path
            for path in class_paths
        }
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                data = future.result()
            except Exception:
                logging.exception("%s generated an exception", path)
            else:
                all_build_paths.extend(data)
    return all_build_paths


# Slot number to gear type mapping for the D4 planner profile
SLOT_TYPE_MAP: dict[int, str] = {
    4: "helm",
    5: "chest",
    8: "weapon",
    9: "weapon",
    10: "weapon",
    11: "weapon",
    12: "weapon",
    13: "gloves",
    14: "pants",
    15: "boots",
    16: "ring",
    17: "ring",
    18: "amulet",
}


def _item_id_to_type(item_id: str) -> str:
    """Derive gear type from a planner item ID prefix."""
    item_id_lower = item_id.lower()
    if item_id_lower.startswith("helm"):
        return "helm"
    if item_id_lower.startswith("chest"):
        return "chest"
    if item_id_lower.startswith("gloves"):
        return "gloves"
    if item_id_lower.startswith("pants"):
        return "pants"
    if item_id_lower.startswith("boots"):
        return "boots"
    if item_id_lower.startswith("amulet"):
        return "amulet"
    if item_id_lower.startswith("ring"):
        return "ring"
    if any(item_id_lower.startswith(p) for p in ("1h", "2h", "bow", "crossbow", "staff", "focus", "shield", "totem")):
        return "weapon"
    if item_id_lower.startswith("offhand"):
        return "offhand"
    return "weapon"


def _extract_planner_profile(url: str) -> dict[str, Any] | None:
    """Extract the plannerProfile data from a build guide page."""
    response = requests.get(url, timeout=20)
    if response.status_code != 200:
        logging.error("Failed to get data from %s. Status code: %s", url, response.status_code)
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup.find_all("script"):
        text = script.string or ""
        if "plannerProfile" not in text:
            continue
        match = re.search(r"window\.__remixContext\s*=\s*(.+)", text, re.DOTALL)
        if not match:
            continue
        raw = match.group(1).rstrip().rstrip(";")
        ctx = json.loads(raw)
        loader = ctx.get("state", {}).get("loaderData", {})
        post = loader.get("branch-posts", {}).get("post", {})
        blocks = post.get("gutenbergBlock", [])
        if blocks and isinstance(blocks, list):
            return blocks[0].get("plannerProfile")
    return None


def get_table_data(paths: list[str]) -> list[list[str | list[str]]]:
    """Return a list of gear affixes for the given build paths.

    Extracts data from the embedded planner profile JSON.
    Each row is [gear_type, [aspect_ids], affix_nid_list_as_text].
    """
    build_jsons: list[list[str | list[str]]] = []
    for path in paths:
        logging.info("Retrieving gear data from %s", path)
        profile_data = _extract_planner_profile(path)
        if not profile_data:
            logging.warning("No planner profile found for %s", path)
            continue

        data = profile_data.get("data", {})
        if isinstance(data, str):
            data = json.loads(data)

        profiles = data.get("profiles", [])
        items_map = data.get("items", {})
        active_profile_idx = data.get("activeProfile", 0)

        # Find the best profile: prefer "Endgame" or the active one
        target_profile = None
        for p in profiles:
            name = p.get("name", "").lower()
            if "endgame" in name:
                target_profile = p
                break
        if target_profile is None and profiles:
            if isinstance(active_profile_idx, int) and active_profile_idx < len(profiles):
                target_profile = profiles[active_profile_idx]
            else:
                target_profile = profiles[0]

        if not target_profile:
            continue

        profile_items = target_profile.get("items", {})

        for slot_str, item_idx in sorted(profile_items.items(), key=lambda x: int(x[0])):
            slot_num = int(slot_str)
            # Skip talisman/charm slots (20+)
            if slot_num >= 20:
                continue

            item = items_map.get(str(item_idx), {})
            if not item:
                continue

            item_id = item.get("id", "")
            gear_type = SLOT_TYPE_MAP.get(slot_num, _item_id_to_type(item_id))

            # Collect affix NIDs from explicits and tempered
            affix_nids: list[str] = []
            for affix in item.get("explicits", []):
                nid = affix.get("nid")
                if nid:
                    affix_nids.append(str(nid))
            for affix in item.get("tempered", []):
                nid = affix.get("nid")
                if nid:
                    affix_nids.append(str(nid))

            # Get aspect if present
            aspect = item.get("aspect", {})
            aspect_id = aspect.get("id", "") if isinstance(aspect, dict) else ""
            aspects: list[str] = [aspect_id] if aspect_id else []

            # Format affix NIDs as numbered lines (for compatibility with downstream)
            affix_text = "\n".join(f"{i+1}. nid:{nid}" for i, nid in enumerate(affix_nids))

            build_jsons.append([gear_type, aspects, affix_text])

    return build_jsons


def compile_jsons() -> None:
    """Create JSON files for each build path and a master JSON file that contains information about all the builds."""
    # Delete all files in the builds directory
    for file in Path("data/builds").glob("*"):
        file.unlink()

    build_paths = get_all_build_paths()
    build_json = []

    Path("data/builds").mkdir(exist_ok=True)

    with ThreadPoolExecutor() as executor:
        future_to_path = {
            executor.submit(get_table_data, [path]): path for path in build_paths
        }
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                data = future.result()
            except Exception:
                logging.exception("%s generated an exception", path)
            else:
                priorities = data
                title = path.split("/")[-1].replace("-guide", "").replace("-build", "")
                build_json.append({title: path})
                with (Path("data/builds") / f"{title}.json").open("w") as f:
                    json.dump(priorities, f, indent=2)

    with Path("data/builds.json").open("w") as f:
        build_json.sort(key=lambda x: next(iter(x.keys())))
        json.dump(build_json, f, indent=2)


def run() -> None:
    """Run the scraper."""
    compile_jsons()
    Uniques().create_uniques()
    AspectMap().create_map()
    AffixMap().create_map()


if __name__ == "__main__":
    run()
