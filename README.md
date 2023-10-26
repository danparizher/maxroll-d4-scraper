# Diablo IV Scraper

This project is a web scraper that extracts Diablo IV data from maxroll.gg and stores the information about different class builds in JSON files. This project is still a work in progress, and more features will be added in the future.

## Directory Structure

```bash
d4-scraper
├─ data
│  ├─ builds  # (contains the builds for each class)
│  └─ builds.json # (K:V pairs of class name and build URL)
├─ main.py # (main script)
└─ src
   ├─ cleaner.py # (cleans the data)
   ├─ scraper.py # (scrapes the data)
```

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

You can install the prerequisites using pip:

```bash
pip install -r requirements.txt
```

or alternatively, you can use `pip-tools` to install the dependencies:

```bash
pip install pip-tools
pip-sync
```

### Usage

To run the project, you can use the following command:

```bash
python main.py
```
