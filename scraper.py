from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%I:%M:%S",
)


def init_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("--log-level=3")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


def get_class_paths() -> list[str]:
    root = "https://maxroll.gg/d4/build-guides?filter[metas][taxonomy]=taxonomies.metas&filter[metas][value]=d4-endgame&filter[classes][taxonomy]=taxonomies.classes&filter[classes][value]=d4-"
    classes = ["barbarian", "druid", "necromancer", "rogue", "sorcerer"]
    return [root + c for c in classes]


def clear_jsons() -> None:
    # delete the contents of the builds.json file
    with Path("builds.json").open("w") as f:
        json.dump([], f)

    # Delete all files in the builds directory
    for file in Path("builds").glob("*"):
        file.unlink()


def get_build_paths(path: str) -> list[str]:
    logging.info("Retrieving build paths from %s", path)
    driver = init_driver()
    build_paths = []
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

    # create the build_paths.json file if it doesn't exist and write to it. If it already exists, overwrite the data
    # Format should be the build name as the key and the build path as the value
    # Everything after build-guides/ and before -guide is the build name

    build_json = [
        {
            build_path.split("/")[-1].split("-guide")[0]: build_path,
        }
        for build_path in build_paths
    ]

    # populate the build_paths.json file with `build_json`. If the file doesn't exist, create it. If there is existing data, overwrite it
    with Path("builds.json").open("r") as f:
        existing_data = json.load(f)
    existing_data += build_json
    with Path("builds.json").open("w") as f:
        json.dump(existing_data, f)

    return build_paths


# go to every build path and get print the contents within:
# 1. Go to 'https://maxroll.gg/d4/build-guides/hammer-of-the-ancients-barbarian-guide' (Which is the first item in the list)
# 2. There is a table of information with the following headers: Slot, Aspect, Stat Priority
# 3. Table Selector: #main-article > div.table-block > table > tbody
# 4. Return the whole table as a list of lists

# Header: #main-article > div.table-block > table > tbody > tr:nth-child(1)
# Row 1: #main-article > div.table-block > table > tbody > tr:nth-child(2)
# Row 2: #main-article > div.table-block > table > tbody > tr:nth-child(3)


def get_stat_priorities(path: str) -> list[list[str]]:
    try:
        driver = init_driver()
        stat_priorities = []
        driver.get(path)
        # wait for the table to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#main-article > div.table-block > table > tbody",
                ),
            ),
        )
        # get the table
        table = driver.find_element(
            By.CSS_SELECTOR,
            "#main-article > div.table-block > table > tbody",
        )
        # get the rows
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            # get the text from the entire row
            row_text = row.text
            # split the row text into cells
            cells = row_text.split("\n")
            stat_priorities.append(cells)
        driver.quit()
        logging.info("Retrieved stat priorities from %s", path)
    except Exception:
        logging.exception("An error occurred while getting stat priorities")
        return []
    else:
        return stat_priorities



def clean_stat_priorities(
    stat_priorities: list[list[str]],
    build_path: str,
) -> list[list[str]]:
    cleaned_stat_priorities = [
        [
            # remove the unicode characters
            re.sub("\u200d", " ", item).strip()
            for item in sublist
            if item.strip()
        ]
        for sublist in stat_priorities
        # remove unique items, because their stats are consistent
        if all("unique" not in item.lower() for item in sublist)
    ]

    # write the cleaned stat priorities
    if not Path("builds").exists():
        Path("builds").mkdir(parents=True)
    build_name = build_path.split("/")[-1].split("-guide")[0]
    file_path = Path("builds") / f"{build_name}.json"

    if file_path.exists():
        with file_path.open("r") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    existing_data += cleaned_stat_priorities
    with Path(file_path).open("w") as f:
        json.dump(existing_data, f)

    return cleaned_stat_priorities


if __name__ == "__main__":
    print("\033c", end="")
    clear_jsons()
    class_paths = get_class_paths()
    with ThreadPoolExecutor() as executor:
        build_paths = executor.map(get_build_paths, class_paths)
        build_paths = [path for sublist in build_paths for path in sublist]

    logging.info("Retrieving stat priorities, this may take a while...")

    with ThreadPoolExecutor() as executor:
        stat_priorities = executor.map(get_stat_priorities, build_paths)
        stat_priorities = [
            priority for sublist in stat_priorities for priority in sublist
        ]

    logging.info("Cleaning stat priorities...")
    with ThreadPoolExecutor() as executor:
        cleaned_stat_priorities = executor.map(
            clean_stat_priorities,
            stat_priorities,
            build_paths,
        )
    logging.info("Done!")
