import pandas as pd
from helper_functions.utility import MyError, setup_shared_logger
from scraped_data import toy_ACCC_scrapper

# configure the shared logger at application entry point
logger = setup_shared_logger()

# Date from which news releases to be scrapped, in the form day month year, e.g. 01 Jan 2025
date = '01 Jul 2025'

if __name__ == "__main__":
    # 1): Extract news articles from relevant sources

    # a) Extracting news articles from ACCC
    toy_ACCC_scrapper.get_ACCC_press_release(fromdate = date)
    
    # b) Extracting news articles from XXX
    # Scrapper for XXX to be called here
    
    # To augment with scrappers for other sources
    # ...

