"""Retrieves the stat priorities from the website using the following process.

1. Generate a list of class paths (barbarian, druid, necromancer, rogue, sorcerer).
2. For each class path, retrieve the build paths for that class (whirlwind-barbarian, twisting-blades-rogue, etc.)
3. For each build path, retrieve the stat priorities (strength, critical hit chance, etc.)
4. Write the stat priorities to a JSON file in the builds directory.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

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
                    data: dict[str, Any] = future.result()
                    self.uniques.append(data["arStrings"][0]["szText"])
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
            for item in sorted(data, key=lambda item: item["IdName"])
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
            for item in sorted(data, key=lambda item: item["IdName"])
        }


def get_soup(url: str) -> BeautifulSoup | None:
    """Return a BeautifulSoup object from the given URL."""
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        logging.error(
            "Failed to get data from %s. Status code: %s",
            url,
            response.status_code,
        )
        return None
    return BeautifulSoup(response.text, "html.parser")


def generate_class_paths() -> list[str]:
    """Return a list of class paths."""
    root = "https://maxroll.gg/d4/build-guides?filter[metas][taxonomy]=taxonomies.metas&filter[metas][value]=d4-endgame&filter[classes][taxonomy]=taxonomies.classes&filter[classes][value]=d4-"
    classes = ["barbarian", "druid", "necromancer", "rogue", "sorcerer"]
    return [root + c for c in classes]


def init_driver() -> webdriver.Chrome:
    """Return a Chrome webdriver with the required options."""
    options = Options()
    options.add_argument("headless")
    options.add_argument("--log-level=3")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


# This function has to use Selenium because BS4 cannot find the build paths in the HTML
def get_build_paths_for_class(path: str) -> list[str]:
    """Return a list of build paths for the given class path."""
    build_paths = []
    logging.info("Retrieving build paths from %s", path)
    driver = init_driver()
    driver.get(path)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[5]/section/div[1]/div/main/div/div[4]/div/div/div[1]/a",
            ),
        ),
    )
    builds = driver.find_elements(
        By.XPATH,
        "/html/body/div[5]/section/div[1]/div/main/div/div[4]/div/div/div/a",
    )
    build_paths += [
        str(link.get_attribute("href"))
        for link in builds
        if isinstance(link.get_attribute("href"), str)
    ]
    driver.quit()
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


def get_text_lines(tag: Tag) -> str:
    """Return the text from the given HTML tag."""
    for span in tag.find_all("span"):
        span.unwrap()

    tag.smooth()
    lines = [line.strip() for line in tag.get_text(separator="\n").splitlines()]

    with suppress(ValueError):
        i = lines.index("Stat Priority:")
        del lines[: i + 1]

    for i in range(len(lines) - 2, 0, -1):
        line = lines[i]

        if not re.match(
            r"^[\d/\.\s]*\d[\d/\.\s]*[\.:]",
            line,
        ) and not line.lower().startswith(("*", "socket")):
            lines[i - 1] += f" {line}"
            del lines[i]

    return "\n".join(lines)


def parse_aspects(aspects: Tag) -> list[str]:
    """Return a list of aspects from the given HTML tag."""
    return [aspect.text for aspect in aspects.find_all("span", class_="d4-affix")]


def get_table_data(paths: list[str]) -> list[list[str | list[str]]]:
    """Return a list of stat priorities for the given build paths."""
    build_jsons: list[list[str | list[str]]] = []
    for path in paths:
        soup = get_soup(path)
        logging.info("Retrieving stat priorities from %s", path)
        # Define the required class names
        required_class_names = [
            "wp-block-advgb-table",
            "advgb-table-frontend",
            "is-style-stripes",
            "aligncenter",
        ]
        # Find the table that contains the most matching class names. We do this because there may multiple tables on the page.
        table = None
        if soup is not None:
            if tables := soup.find_all("table"):
                table = max(
                    tables,
                    key=lambda tag: sum(
                        c in tag.get("class", []) for c in required_class_names
                    ),
                )
            else:
                table = None
        if table is not None and (tbody := table.find("tbody")):
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) != 3:
                    continue

                slot, aspects, affixes = cols

                # <span class="d4-item" data-d4-id="344413"><span class="d4-gametip"><div class="d4t-sprite-icon"><div class="d4t-icon d4t-items-icon" style="background-position: -7em -11em;"></div></div>‍<span class="d4-color-unique">Hellhammer</span></span></span>
                # <span class="d4-affix" data-d4-id="578875"><span class="d4-gametip"><div class="d4t-sprite-icon"><div class="d4t-icon d4t-aspect-icon" style="background-position-x: -2em;"></div></div>‍<span class="d4-color-legendary">Edgemaster’s Aspect</span></span></span>
                # unique items in the aspects column

                if aspects.find_all("span", class_="d4-item") and not aspects.find_all(
                    "span",
                    class_="d4-affix",
                ):
                    continue

                build_jsons.append(
                    [
                        get_text_lines(slot),
                        parse_aspects(aspects)
                        if aspects.find_all("span", class_="d4-affix")
                        else get_text_lines(aspects),
                        get_text_lines(affixes),
                    ],
                )
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
        build_json = sorted(build_json, key=lambda x: next(iter(x.keys())))
        json.dump(build_json, f, indent=2)


def run() -> None:
    """Run the scraper."""
    compile_jsons()
    Uniques().create_uniques()
    AspectMap().create_map()
    AffixMap().create_map()


if __name__ == "__main__":
    run()
