import json, openai, os, sqlite3
import pandas as pd
import time
from groq import Groq
from helper_functions.utility import MyError, setup_shared_logger, llm_output, Groq_model, Groq_client, OAI_model, OAI_client, tempscrappedfolder, tablename, dbfolder, WIPfolder
from helper_functions.utility import classifier_sys_msg
from openai import OpenAI
from pathlib import Path
from pydantic import BaseModel, Field
from tqdm.auto import tqdm
from typing import Annotated, Dict, List, Optional, Union
from typing_extensions import Literal

tqdm.pandas()

# Set up the shared logger
logger = setup_shared_logger()

# Create database folder, if it does't exist
Path(dbfolder).mkdir(parents=True, exist_ok=True)
# Create temp folder, if it does't exist
Path(WIPfolder).mkdir(parents=True, exist_ok=True)


class classifier_response(BaseModel):
    """Pydantic response class to ensure that LLM always responds in the same format."""
    Reasons: str = Field(..., description="A concise yet precise reasoning and justification as to whether given text is merger and acquisition related.")
    Merger_Related: Literal['true', 'false', 'unable to tell'] = Field(...,description="Respond 'true' if given text is merger and acquisition related, 'false' if otherwise. If unsure even after providing reasoning, reply 'unable to tell'.")
    Merger_Entities: Optional[List[str]] = Field(..., description="Captures the list of names of parties involved, if given text is merger and acquisition related.")


if __name__ == "__main__":
    dfs = []
    try:
        # 1) Read in the CSV files in the scraped_data folder
        # Define the path to the folder containing the CSV files
        directory_path = Path(tempscrappedfolder).absolute()

        # Find all CSV files in the specified folder and read them into DataFrames
        for file_path in directory_path.glob("**/*.csv"):
            try:
                df = pd.read_csv(file_path)
                dfs.append(df)
                logger.info(f"Successfully read: {file_path} for further processing")
            except (Exception, BaseException) as e:
                raise MyError(f"Error reading {file_path}: {e}")

        # Concatenate all DataFrames into a single DataFrame
        if len(dfs) == 0:
            logger.warning(f"No CSV files found in folder '{tempscrappedfolder}'.")
        else:
            combined_df = pd.concat(dfs, ignore_index=True)

        # 2) Establish connection to database 
            conn = sqlite3.connect(f'{dbfolder}/data.db')
            cursor = conn.cursor()

        # Check if the database table containing the scrapped data and relevant information exists
            tablelist = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            if f'{tablename}' not in [table[0] for table in tablelist]:
                pass
        # if there is historical data, check and remove potential duplicates with the data scraped during the most recent run
            else:
                query = f"SELECT Published_Date, Text FROM {tablename} WHERE Extracted_Date = (SELECT MAX(Extracted_Date) FROM {tablename})" # consider if need to include Source for comparison
                past_df = pd.read_sql_query(query, conn)
                combined_df = combined_df[~((combined_df['Text'].isin(past_df['Text'])) & (combined_df['Published_Date'].isin(past_df['Published_Date'])))]
            
            if len(combined_df) == 0:  #skip if there is no data
                    logger.info("No new article to be classified")
            else:
            # 3) Pass the text in each data point in the combined DataFrame to LLM to decide if the text is related to merger and acquisition, and if so, extract the entities involved
            
            # Check the number of data points, for small dataset, can use free version of Groq models, larger dataset, use OpenAI 
                if len(combined_df) <= 200:
            # Use Groq
            # Calculate the delay based on Groq rate limit, meta-llama/llama-4-scout-17b-16e-instruct-> 30(RPM), 1K(RPD), 30K(TPM), 500K(TPD)
                    rate_limit_per_minute = 30
                    delay = 60.0 / rate_limit_per_minute
                    combined_df['response'] = combined_df.progress_apply(lambda x: json.loads(llm_output(client=Groq_client, model=Groq_model, 
                                                        sys_msg=classifier_sys_msg, input=x['Text'], schema=classifier_response, 
                                                        delay_in_seconds=delay).output_text), axis=1)
                else:
            # Use OpenAI
            # Determine the delay to be 1sec based on OpenAI Tier 1 rate limit, gpt-4o-mini -> Tier1:	500 (RPM) , 10,000 (RPD), 200,000 (TPM).
                    combined_df['response'] = combined_df.progress_apply(lambda x: json.loads(llm_output(client = OAI_client, model=OAI_model,
                                                        sys_msg=classifier_sys_msg, input=x['Text'], schema=classifier_response).output_text), axis=1)
            
            # Expand the 'response' column
                expanded_response = combined_df['response'].apply(pd.Series)
            # Combine with the original DataFrame
                df_final = pd.concat([combined_df.drop(['response'], axis=1), expanded_response], axis=1)
                df_final['Merger_Entities'] = df_final['Merger_Entities'].apply(lambda x: ',| '.join(x) if x is not None and len(x)>1 else '')

            # Write to CSV in temp folder
                df_final.to_csv(os.path.join(WIPfolder,'classified_media_releases.csv'), index=False)
                df_final.to_sql(f'{tablename}', con=conn, if_exists='append', index=False)
            
            # Update log upon successful execution
                logger.info(f"{str(len(combined_df))} articles successfully classified")
    
    except MyError as e:
        logger.error(f"{e}")
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
    except (Exception, BaseException) as e:
        logger.error(f"General Error: {e}")
    
    finally:
    # Ensure the database connection is closed
        if conn:
            conn.close()
            logger.info('SQLite Connection closed')