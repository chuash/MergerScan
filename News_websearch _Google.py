# Import relevant libraries
import asyncio, json, openai, os, sqlite3
import pandas as pd
import time
from groq import Groq
from google import genai
from google.genai import errors
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig, GenerateContentResponse, GroundingChunk, GroundingSupport
from helper_functions.utility import (MyError, setup_shared_logger, Groq_model, Groq_client, OAI_model, OAI_client, 
                                      async_Groq_client, async_OAI_client, async_Perplexity_client, Perplexity_model, 
                                      async_llm_output, tablename, dbfolder, WIPfolder, Gemini_model, Google_client)
from helper_functions.prompts import (websearch_raw_sys_msg, query1_structoutput_sys_msg, Query1_user_input, Query2_user_input, 
                                      Query3_user_input)
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion
from pathlib import Path
from pydantic import BaseModel, Field
from strip_markdown import strip_markdown
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
    explanation: str = Field(..., description="Detailed explanation, capturing all the citations denoted by [citation source number], to justify the response given for list of goods and services and corresponding brand names, currently sold or provided in Singapore")
    goods_services_sold_in_Singapore:str = Field(..., description="Captures ONLY the list of goods and services the named merger party currently sells or provides in Singapore. To indicate 'None', if the named merger party does not sell anything in Singapore.")
    brand_names:str=Field(..., description="Captures the brand names of the goods and services the named merger party currently sells or provides in Singapore. To indicate 'None', if the named merger party does not sell anything in Singapore.")

class query1_response(BaseModel):
    """Pydantic response class to ensure that LLM always responds in the same format."""
    response: List[query1_base_response] = Field(..., description="Captures the search result for each named merger party involved in the merger case")

#class query2_response(BaseModel):
#    """Pydantic response class to ensure that LLM always responds in the same format."""
#    explanation: str = Field(..., description="Explanation to justify response given for list of common goods and services in Singapore")
#    common_goods_services_in_Singapore: str = Field(..., description="Captures only the common goods and services (including the respective brand names), if any, that all merger parties sell or provide in Singapore. To indicate 'None', if there is no common goods or services.")
    
#class query3_response(BaseModel):
#    """Pydantic response class to ensure that LLM always responds in the same format."""
#    explanation: str = Field(..., description="Detailed explanation, with citations given by [citation source number], why the merger parties could be potential competitors (e.g., similar products overseas, capability, or actual plans to enter the market)") 
#    potential_goods_services_in_Singapore: str = Field(..., description="Captures any goods or services where these merger parties could potentially compete in Singapore, even if they do not currently sell those goods or services here. To indicate 'None', if there is no such assessed potential")

def add_citations(text:str, supports:GroundingSupport, chunks:GroundingChunk)->str:
    """Adds citations inline into the response text"""

    # Sort supports by end_index in descending order to avoid shifting issues when inserting.
    sorted_supports = sorted(supports, key=lambda s: s.segment.end_index, reverse=True)

    for support in sorted_supports:
        end_index = support.segment.end_index
        if support.grounding_chunk_indices:
            # Create citation index like [1]..[2]..
            citation_links = []
            for i in support.grounding_chunk_indices:
                if i < len(chunks):
                    #uri = chunks[i].web.uri
                    citation_links.append(f"[{i + 1}]")
                    #citation_links.append(f"[{i + 1}]({uri})")

            citation_string = ",".join(citation_links) + ' '
            text = text[:end_index] + citation_string + text[end_index:]

    return text


async def async_gemini_search(client:genai, model:str, query:str, sysmsg:str=websearch_raw_sys_msg, temperature:float=0.0)->GenerateContentResponse:
    """Enables asynchronous google search using Gemini API"""

    grounding_tool = Tool(google_search=GoogleSearch())

    try:
      response = await client.aio.models.generate_content(
                    model=model,
                    contents=query,
                    config = GenerateContentConfig(
                              system_instruction=sysmsg,
                              #max_output_tokens=2048,   # avoid setting the max_output_tokens in case some responses from the reasoning model overshoots the max tokens, then will get incomplete response
                              temperature=0.0,
                              #frequency_penalty=0.1,  # not supported by Gemini 2.5 flash
                              tools=[grounding_tool],
                            )  
                    )
      
      return response
    
    except errors.APIError as e:
       raise MyError(f"async_gemini_search function API error: {e}, while processing text '{query}'")
    except (Exception, BaseException) as e:
       raise MyError(f"async_gemini_search function error: {e}, while processing text '{query}'")


async def websearch(chunk:List)-> List[Any]:
    """Processes a list of Gemini web search requests asynchronously."""
    tasks = [async_gemini_search(client=Google_client, model=Gemini_model,query=p) for p in chunk]
    results = await tqdm_asyncio.gather(*tasks, desc="Processing web search tasks")
    return results


async def structured_output(chunk:List)-> List[Any]:
    """Processes a list of LLM requests asynchronously."""
    tasks = [async_llm_output(client=async_OAI_client, model=OAI_model, prompt_messages=p, schema=query1_response) for p in chunk]
    results = await tqdm_asyncio.gather(*tasks, desc="Processing structured output tasks")
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
    """Generate list of list of corresponding system and user prompts to be sent to LLM as chat completion messages"""
    prompt_message_list = []
    for item in data_list:
        prompt_message_list.append([{"role": "system", "content": f"{sys_msg}"},{"role": "user", "content": f"<incoming-text>{item}</incoming-text>"}])
    return prompt_message_list


def process_search(response:GenerateContentResponse)->dict:
    """Extract and retain only relevant information from Google search response"""
    text = response.text
    supports = response.candidates[0].grounding_metadata.grounding_supports
    chunks = response.candidates[0].grounding_metadata.grounding_chunks
    web_search_title_url = [(chunk.web.title,chunk.web.uri)  for chunk in chunks]
    #web_search_queries = response.candidates[0].grounding_metadata.web_search_queries
    usage_metadata = response.usage_metadata
    text_with_citations = add_citations(text, supports, chunks)
      
    return {'text': text, 'text_with_citations': text_with_citations, 'title_url': web_search_title_url, 'usage':usage_metadata}


tempfilepath = os.path.join(WIPfolder,f'{tablename}_websearch.csv')

if __name__ == "__main__":
    try:
        #0) Establish connection to database
        conn = sqlite3.connect(f'{dbfolder}/data.db')
        cursor = conn.cursor()
        
        #1) Check if tempfilepath exists, if not read from database and filter for merger related news with identified entities
        if os.path.exists(tempfilepath):
            df1 = pd.read_csv(tempfilepath).fillna('')
        else:
            sqlquery = f"SELECT Published_Date, Source, Extracted_Date, Text, Merger_Related, Merger_Entities FROM {tablename} WHERE Extracted_Date = (SELECT MAX(Extracted_Date) FROM {tablename})"    
            df = pd.read_sql_query(sqlquery, con=conn)
            df1 = df[(df['Merger_Related']=='true') & (df['Merger_Entities']!='')].reset_index(inplace=False).drop('index', axis=1)
        
        if len(df1) == 0:  #skip if there is no merger related news article
            logger.warning("No new merger related article to conduct web search for")
        else:
        #2) Extract the corresponding news source - entities pairs
            org_entities = df1[['Source','Merger_Entities']].apply(tuple, axis=1).to_list()

            if 'Query1' in df1.columns:
                pass
            else:
        #3a) Generate query 1 user prompt messages for each of the identified merger-related news , using the query 1 text supplied by user
                query1_list = []
                
                for item in org_entities:
                    query1_list.append(f"<incoming-text>The following parties ({item[1]}) are involved in the same merger case handled by {item[0]}. {Query1_user_input} Avoid markdown in reply. </incoming-text>")
                logger.info(f"List of {len(query1_list)} query 1 prompt messages successfully generated.")
            
                #3b) Execute Google search for query 1 asynchronously, then parse the processed Google responses via another LLM in order to produce structured outputs with citations
                # Google API @ Tier 1 are subject to rate limit of 1K RPM
                query1_websearch_results = asyncio.run(main(data_list=query1_list, func=websearch, chunk_size=20, pause_duration=1))
                logger.info("Web search for query 1 successfully executed. Preparing to parse Google responses via another LLM.")
                # Processing the Google search responses
                query1_websearch_results_processed = [process_search(response) for response in query1_websearch_results]

                query1_struct_prompt_message_list = prompt_generator(data_list=[strip_markdown(item['text_with_citations']) for item in query1_websearch_results_processed], sys_msg=query1_structoutput_sys_msg)
                # gpt-4o-mini (Tier 1) is subject to rate limits : 500 (RPM), 10K (RPD), 200L (TPM).
                struct_query1_websearch_results = asyncio.run(main(data_list=query1_struct_prompt_message_list,func=structured_output, chunk_size=10, pause_duration=1))  # can use larger chunks and shorter duration subject to limit of 500 RPM
                logger.info("Web search with structured output for query 1 successfully executed")
                
                #3c)  Combine raw Google search response with the structured output, then append to dataframe
                query1_combined_results = [str((x['text_with_citations'], x['title_url'], y.choices[0].message.content)) for x, y in zip(query1_websearch_results_processed, struct_query1_websearch_results)]
                df1['Query1'] = query1_combined_results

                #3d) Write to temporary CSV and also to database.
                df1.to_csv(tempfilepath, index=False)
                #df1.drop(['Merger_Related', 'Merger_Entities'], axis=1).to_sql(f'{tablename}_websearch_query1', con=conn, if_exists='append', index=False)

        #4a) Carry on for the next few questions, 2, 3, 4

        # Write to database
        #df_final = pd.merge(df, df1.drop(['Merger_Related', 'Merger_Entities'], axis=1), on=['Published_Date', 'Source', 'Text'], how='left').fillna('')
        #df_final.to_sql(f'media_releases_websearch', con=conn, if_exists='append', index=False)

    except MyError as e:
        logger.error(f"Error while executing {os.path.basename(__file__)}: {e}")
    except sqlite3.Error as e:
        logger.error(f"Database connection error while executing {os.path.basename(__file__)}: {e}")
    except (Exception, BaseException) as e:
        logger.error(f"Error while executing {os.path.basename(__file__)}: {e}")
    
    finally:
    # Ensure the database connection is closed
        if conn:
            conn.close()
            logger.info('SQLite Connection closed')