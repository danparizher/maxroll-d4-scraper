"""
This is the entry point for the application.
"""

from src import cleaner, scraper, translator

scraper.run()
cleaner.run()
translator.run()
