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
from concurrent.futures import ThreadPoolExecutor
from itertools import chain
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


def get_soup(url: str) -> BeautifulSoup:
    """Return a BeautifulSoup object from the given URL."""
    r = requests.get(url, timeout=5)
    return BeautifulSoup(r.text, "html.parser")


def generate_class_paths() -> list[str]:
    """Return a list of class paths."""
    root = "https://maxroll.gg/d4/build-guides?filter[metas][taxonomy]=taxonomies.metas&filter[metas][value]=d4-endgame&filter[classes][taxonomy]=taxonomies.classes&filter[classes][value]=d4-"
    classes = ["barbarian", "druid", "necromancer", "rogue", "sorcerer"]
    return [root + c for c in classes]


def init_driver() -> webdriver.Chrome:
    """Return a Chrome webdriver with the required options."""
    options = webdriver.ChromeOptions()
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
    build_paths += [link.get_attribute("href") for link in builds]
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


def get_stat_priorities(paths: list[str]) -> list[list[str]]:
    """Return a list of stat priorities for the given build paths."""
    build_jsons = []
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
        table = max(
            soup.find_all("table"),
            key=lambda tag: sum(
                c in tag.get("class", []) for c in required_class_names
            ),
        )
        if table is not None:
            tbody = table.find("tbody")
            if tbody is not None:
                build_jsons.append(
                    [
                        [
                            stat.text
                            for stat in stat_priority.find_all("td")
                            if stat.text
                        ]
                        for stat_priority in tbody.find_all("tr")
                    ],
                )
    return list(chain.from_iterable(build_jsons))


def build_jsons() -> None:
    """Create JSON files for each build path and a master JSON file that contains information about all the builds."""
    # Delete all files in the builds directory
    for file in Path("data\\builds").glob("*"):
        file.unlink()

    build_paths = get_all_build_paths()
    build_json = []

    Path("data\\builds").mkdir(exist_ok=True)

    with ThreadPoolExecutor() as executor:
        future_to_path = {
            executor.submit(get_stat_priorities, [path]): path for path in build_paths
        }
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                data = future.result()
            except Exception:
                logging.exception("%s generated an exception", path)
            else:
                priorities = data
                title = path.split("/")[-1].split("-guide")[0]
                build_json.append({title: path})
                with (Path("data\\builds") / f"{title}.json").open("w") as f:
                    json.dump(priorities, f, indent=2)

    with Path("data\\builds.json").open("w") as f:
        build_json = sorted(build_json, key=lambda x: next(iter(x.keys())))
        json.dump(build_json, f, indent=2)


def run() -> None:
    """Run the scraper."""
    build_jsons()


if __name__ == "__main__":
    run()
