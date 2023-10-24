from __future__ import annotations

import concurrent.futures
import json
import logging
from concurrent.futures import ThreadPoolExecutor
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
    r = requests.get(url, timeout=5)
    return BeautifulSoup(r.text, "html.parser")


def get_class_paths() -> list[str]:
    root = "https://maxroll.gg/d4/build-guides?filter[metas][taxonomy]=taxonomies.metas&filter[metas][value]=d4-endgame&filter[classes][taxonomy]=taxonomies.classes&filter[classes][value]=d4-"
    classes = ["barbarian", "druid", "necromancer", "rogue", "sorcerer"]
    return [root + c for c in classes]


def init_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("--log-level=3")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


def get_build_paths_for_class(path: str) -> list[str]:
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


def get_build_paths() -> list[str]:
    all_build_paths = []
    class_paths = get_class_paths()
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
    build_jsons = []
    for path in paths:
        soup = get_soup(path)
        logging.info("Retrieving stat priorities from %s", path)
        build_jsons.append(
            [
                [stat.text for stat in stat_priority.find_all("td") if stat.text]
                for stat_priority in soup.find_all("tbody")[0].find_all("tr")
            ],
        )
    return build_jsons


def build_jsons() -> None:
    # Delete all files in the builds directory
    for file in Path("builds").glob("*"):
        file.unlink()

    build_paths = get_build_paths()
    build_json = []

    Path("builds").mkdir(exist_ok=True)

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
                priorities = data[0]  # Assuming there's only one path in the list
                title = path.split("/")[-1].split("-guide")[0]
                build_json.append({title: path})
                with (Path("builds") / f"{title}.json").open("w") as f:
                    json.dump(priorities, f, indent=2)

    with Path("builds.json").open("w") as f:
        build_json = sorted(build_json, key=lambda x: next(iter(x.keys())))
        json.dump(build_json, f, indent=2)


if __name__ == "__main__":
    build_jsons()
