import json, os
import pandas as pd
import uuid
from datetime import date
from groq import Groq
from helper_functions.utility import MyError, count_tokens, check_for_malicious_intent
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage,ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch, TavilyExtract
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph, START
from langgraph.prebuilt import create_react_agent, tools_condition, ToolNode
from strip_markdown import strip_markdown
from openai import OpenAI
from openai.types.chat import ChatCompletion
from operator import add
from typing import Annotated, Dict, List, Optional, Union
from typing_extensions import Literal

# Set up the shared logger
logger = setup_shared_logger()