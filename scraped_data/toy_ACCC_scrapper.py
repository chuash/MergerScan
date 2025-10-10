# Initialising relevant libraries
import pandas as pd
import logging, os, random, requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List

# list of user agents to be used when executing html request
_user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Function to extract titles and first paragraphs from ACCC media press releases
def get_ACCC_press_release(fromdate: str, user_agents:List[str]=_user_agents)->pd.DataFrame:
    # Retrieving the shared logger
    logger = logging.getLogger('shared_app_logger')
    # initialising an empty list to contain the desired media releases
    listing = []
    # randomising the user agent to be added to the request header
    headers = {"User-Agent": random.choice(user_agents)}
    
    try:
        i = 0
        while True:
            # Start from the first page which also contains the most recent news release
            url = f"https://www.accc.gov.au/news-centre?type=accc_news&layout=full_width&items_per_page=25&page={i}"
            response = requests.get(url, headers=headers)
            # raises error in the event of bad responses
            response.raise_for_status()
            # parses the extracted html
            soup = BeautifulSoup(response.text, "html.parser")
        
            # Get the published dates for all the news listings on the page
            date = soup.find_all("div", class_="accc-date-card__header col-12 col-md-2")
            date_component = [{"Published Date": ele.find("span", class_="accc-date-card--publish--day").get_text().strip() + ' ' + 
                            ele.find("span", class_="accc-date-card--publish--month").get_text().strip() + ' ' + 
                            ele.find("span", class_="accc-date-card--publish--year").get_text().strip()} for ele in date]
        
            # Get the titles and first paragraphs for all the news listings on the page
            content = soup.find_all("div", class_="accc-date-card__body col-12 col-md-10")
            text_component = [{"Text": ele.find("div", class_="field--name-node-title").get_text().strip() + '. ' + 
                            ele.find("div", class_="field--name-field-acccgov-summary").get_text().strip()} for ele in content]
        
            # Associate the published dates to the corresponding news listings
            news_extract = [item[0]|item[1] for item in zip(date_component,text_component)]
            listing.extend(news_extract)

            # If the last published date on the page is still after the user input date, then continue to the next page
            # Else stop if the last published date is earlier
            if datetime.strptime(date_component[-1]['Published Date'], '%d %b %Y') >= datetime.strptime(fromdate, '%d %b %Y'):
                i = i+1
            else:
                break

        # convert to dataframe
        df= pd.DataFrame(listing)
        # Filter for all news listing after the specified date
        df= df[pd.to_datetime(df['Published Date']) >= datetime.strptime(fromdate, '%d %b %Y')]
        # Add the news source
        df['Source'] = 'ACCC'
        df = df[['Published Date', 'Source', 'Text']]
        # Export as csv
        df.to_csv(os.path.join('scraped_data',f'ACCC_from_{fromdate}.csv'), index=False)
        # Update log upon successful scraping
        logger.info(f"Media releases dated from '{fromdate}' successfully downloaded from ACCC")
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"ACCC- Network connection error: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"ACCC - Request timed out: {e}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"ACCC - HTTP error: {e}")
        logger.error(f"\n Server response: {e.response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"ACCC - An unexpected Requests error occurred: {e}")
    except Exception as e:
        logger.error(f"ACCC - An unexpected general error occurred: {e}")