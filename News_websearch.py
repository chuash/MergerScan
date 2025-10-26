import asyncio, json, openai, sqlite3
import pandas as pd
import time
from groq import Groq
from helper_functions.utility import (MyError, setup_shared_logger, Groq_model, Groq_client, OAI_model, OAI_client, 
                                      async_Groq_client, async_OAI_client, async_Perplexity_client, Perplexity_model, 
                                      async_llm_output, tablename, tablename_websearch, dbfolder)
from helper_functions.prompts import (websearch_raw_sys_msg, query1_structoutput_sys_msg, query1_user_input, query2_user_input, 
                                      query3_user_input)
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion
from pathlib import Path
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm_asyncio
from tqdm.auto import tqdm
from typing import Dict, List, Any
from typing_extensions import Literal

# Set up the shared logger
logger = setup_shared_logger()

# Set up structured LLM output schemas
class query1_base_response(BaseModel):
    """Pydantic response class to ensure that LLM always responds in the same format."""
    merger_party:str = Field(..., description="Name of merger party involved in the merger case")
    explanation: str = Field(..., description="Detailed explanation, with citations given by [citation source number], to justify response given for list of goods and services currently sold or provided in Singapore")
    goods_services_sold_in_Singapore:str = Field(..., description="Captures ONLY the list of goods and services (including respective brand names) the named merger party currently sells or provides in Singapore. To indicate 'None', if the named merger party does not sell anything in Singapore.")

class query1_response(BaseModel):
    """Pydantic response class to ensure that LLM always responds in the same format."""
    response: List[query1_base_response] = Field(..., description="Captures the search result for each named merger party involved in the merger case")

class query2_response(BaseModel):
    """Pydantic response class to ensure that LLM always responds in the same format."""
    explanation: str = Field(..., description="Explanation to justify response given for list of common goods and services in Singapore")
    common_goods_services_in_Singapore: str = Field(..., description="Captures only the common goods and services (including the respective brand names), if any, that all merger parties sell or provide in Singapore. To indicate 'None', if there is no common goods or services.")
    
class query3_response(BaseModel):
    """Pydantic response class to ensure that LLM always responds in the same format."""
    explanation: str = Field(..., description="Detailed explanation, with citations given by [citation source number], why the merger parties could be potential competitors (e.g., similar products overseas, capability, or actual plans to enter the market)") 
    potential_goods_services_in_Singapore: str = Field(..., description="Captures any goods or services where these merger parties could potentially compete in Singapore, even if they do not currently sell those goods or services here. To indicate 'None', if there is no such assessed potential")


async def async_perplexity_search(client:OpenAI, model:str, prompt_messages:List[Dict], schema:BaseModel|None = None, searchmode:str="web", temperature:float=0.1, 
                    maxtokens:int=1024, search_domain:List[str]=[], related_questions:bool=False, presence_penalty:float=0.1, frequency_penalty:float=0.1,
                    search_classifier:bool=True, search_context:str="medium") -> BaseModel|ChatCompletion:
        """Enables asynchronous access to Perplexity API"""
        try:
            if schema:
                 output_json_structure = {
                                       "type": "json_schema",
                                       "json_schema": {"schema": schema.model_json_schema()}
                                        }
            else:
                output_json_structure = None

            response = await client.chat.completions.create(
                model=model,
                messages=prompt_messages,
                extra_body={
                    "search_mode": searchmode,
                    "max_tokens": maxtokens,
                    "temperature": temperature,
                    "search_domain_filter": search_domain,
                    "return_related_questions": related_questions,
                    #"presence_penalty": presence_penalty,
                    "frequency_penalty": frequency_penalty,
                    "enable_search_classifier": search_classifier,
                    "web_search_options": {"search_context_size": search_context},
                    "max_search_results": 10},
                response_format = output_json_structure)
            return response
        
        except openai.APIError as e:
            raise MyError(f"API Error: {e}, while processing text '{prompt_messages[1]['content']}'")
        except (Exception, BaseException) as e:
            raise MyError(f"Error: {e}, while processing text '{prompt_messages[1]['content']}'")

async def websearch(chunk:List)-> List[Any]:
    """Processes a list of query requests concurrently by Perplexity."""
    tasks = [async_perplexity_search(client=async_Perplexity_client, model=Perplexity_model, prompt_messages=p, schema=None) for p in chunk]
    results = await tqdm_asyncio.gather(*tasks, desc="Processing tasks")
    return results

async def structured_output(chunk:List)-> List[Any]:
    """Processes a list of LLM requests concurrently."""
    tasks = [async_llm_output(client=async_OAI_client, model=OAI_model, prompt_messages=p, schema=query1_response) for p in chunk]
    results = await tqdm_asyncio.gather(*tasks, desc="Processing tasks")
    return results

# main asynchronous function to iterate through the data list in chunks
async def main(data_list:List, func, chunk_size:int, pause_duration:float)-> List[Any]:
    """Processes data list in chunks with pauses between chunks."""
    results = []
    for i in range(0, len(data_list), chunk_size):
        chunk = data_list[i:i + chunk_size]
        chunk_results = await func(chunk)
        results.extend(chunk_results)
        if i + chunk_size < len(data_list):  # Don't pause after the last chunk
            print(f"Pausing for {pause_duration} seconds, after processing chunk[{str(i)}:{str(i+chunk_size)}]")
            await asyncio.sleep(pause_duration)
    return results

def prompt_generator(data_list:List, sys_msg:str)->List[List[Dict]]:
    """Generate list of list of corresponding system and user prompts to be sent to LLM or Perplexity as chat completion messages"""
    prompt_message_list = []
    for item in data_list:
        prompt_message_list.append([{"role": "system", "content": f"{sys_msg}"},{"role": "user", "content": f"<incoming-text>{item}</incoming-text>"}])
    return prompt_message_list


if __name__ == "__main__":
    try:
        #1) Establish connection to database and read in data from table
        conn = sqlite3.connect(f'{dbfolder}/data.db')
        cursor = conn.cursor()
        sqlquery = f"SELECT Published_Date, Source, Text, Merger_Related, Merger_Entities FROM {tablename} WHERE Extracted_Date = (SELECT MAX(Extracted_Date) FROM {tablename})"
        df = pd.read_sql_query(sqlquery, con=conn)

        #2) Filter for merger related news with identified entities, and extract the corresponding news source - entities pairs 
        df1 = df[(df['Merger_Related']=='true') & (df['Merger_Entities']!='')].reset_index(inplace=False).drop('index', axis=1)
        org_entities = df1[['Source','entities']].apply(tuple, axis=1).to_list()

        #3a) Generate query 1 prompt messages using user inputs for query 1
        query1_list = []
        for item in org_entities:
            query1_list.append(f"The following parties ({item[1]}) are involved in the same merger case handled by {item[0]}. {query1_user_input}")
        query1_prompt_message_list = prompt_generator(data_list=query1_list, sys_msg=websearch_raw_sys_msg)

        #3b) Execute Perplexity search for query 1 asynchronously
        query1_websearch_results = asyncio.run(main(data_list=query1_prompt_message_list, func=websearch, chunk_size=10, pause_duration=1))

        #3c) 
        #struct_prompt_message_list = prompt_generator(data_list=[strip_markdown(item.choices[0].message.content) for item in websearchresults], sys_msg=structoutput_sys_msg)
#struct_prompt_message_list




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