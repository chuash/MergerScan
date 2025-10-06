from helper_functions.utility import MyError, setup_shared_logger
from Data import toy_ACCC_scrapper

# configure the shared logger at application entry point (to be changed later)
logger = setup_shared_logger()

# Extracting media releases from ACCC
toy_ACCC_scrapper.get_ACCC_press_release(fromdate = '01 Jul 2025')
