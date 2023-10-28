# Diablo IV Scraper

The "Diablo IV Scraper" is a Python-based web scraping project that extracts and processes data from the website [maxroll.gg](https://maxroll.gg/d4), which provides information about the game Diablo IV. The primary focus of the data extraction is on the different class builds available in the game.

The project is structured into three main components: scraping, cleaning, and translating the data. The scraping is done using `BeautifulSoup` and `Selenium`, which extract the data from the website. The cleaning process involves refining the scraped data to make it more usable and structured. The translating process converts the cleaned data into a format compatible with [D4Companion](https://github.com/josdemmers/Diablo4Companion).

The extracted, cleaned, and translated data is stored in JSON files, organized by class builds and other game elements like unique items and stats. This data can be used for various purposes, such as analysis of game mechanics, build optimization, or integration with other tools or services related to Diablo IV.

The project is still a work in progress, with plans for additional features and improvements in the future.

## Directory Structure

```bash
d4-scraper
├─ data
│  ├─ builds  # (contains the builds for each class)
│  ├─ translated_builds # (contains the D4Companion compatible builds)
│  ├─ builds.json # (K:V pairs of class name and build URL)
│  ├─ stat_map.json # (K:V pairs of statID and stat name)
│  └─ uniques.json # (List of all unique items)
├─ main.py # (main script)
└─ src
   ├─ scraper.py # (scrapes the data)
   ├─ cleaner.py # (cleans the data)
   └─ translator.py # (translates the data)
```

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

You can install the prerequisites using pip:

```bash
pip install -r requirements.txt
```

Alternatively, you can use [`pip-tools`](https://pypi.org/project/pip-tools/) to install the dependencies:

```bash
pip install pip-tools
pip-sync
```

### Usage

To run the project, you can use the following command:

```bash
python main.py
```
