import asyncio, json, openai, sqlite3
import pandas as pd
import time
from groq import Groq
from helper_functions.utility import (MyError, setup_shared_logger, Groq_model, Groq_client, OAI_model, OAI_client, 
                                      tablename, tablename_websearch, dbfolder)
from openai import OpenAI, AsyncOpenAI
from pathlib import Path
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm_asyncio
from tqdm.auto import tqdm
from typing import Dict, List
from typing_extensions import Literal

# Set up the shared logger
logger = setup_shared_logger()

# Set up structured output schemas
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

