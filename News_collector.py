# import libraries
import os
import pandas as pd
from helper_functions.utility import MyError, setup_shared_logger, set_collection_date, tempscrappedfolder
from pathlib import Path
from scrapers import ACCC_scrapper

# Set up the shared logger
logger = setup_shared_logger()

# Set the date from which news are to be scrapped, in the format day month year, e.g. 01 Jan 2025 or None
scrapped_from_date =  '01 Sep 2025'     # or None
date = set_collection_date(date=scrapped_from_date)

# Create folder used to temporarily store scrapped data, if it does't exist
Path(tempscrappedfolder).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    try:
        # 1): Extract news articles from relevant sources
        # a) Extracting news articles from ACCC
        ACCC_scrapper.get_ACCC_press_release(fromdate = date, folder=tempscrappedfolder)
        
        # b) Extracting news articles from X
        # Scrapper for X to be called here. To augment with scrappers for other sources
        
    except MyError as e:
        logger.error(f"{e}")
    except (Exception, BaseException) as e:
        logger.error(f"General error while executing {os.path.basename(__file__)} : {e}")

