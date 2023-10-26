"""
This is the entry point for the application.
"""

from src import scraper
from src.cleaner import Cleaner
from src.translator import Translator

if __name__ == "__main__":
    scraper.run()
    cleaner = Cleaner()
    cleaner.run()
    translator = Translator()
    translator.run()
