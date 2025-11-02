# Import relevant libraries
import json, os, openai, sqlite3
import pandas as pd
import uuid
from datetime import datetime, date
from groq import Groq
from helper_functions.utility import (Chat_OAI_llm, Groq_client, Groq_model, OAI_client, OAI_model, dbfolder, MyError, 
                                      setup_shared_logger, count_tokens, check_for_malicious_intent)
from helper_functions.prompts import chatagent_sys_msg
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch, TavilyExtract
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph, START
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent, tools_condition, ToolNode
from strip_markdown import strip_markdown
from openai import OpenAI
from openai.types.chat import ChatCompletion
from operator import add
from typing import Annotated, Dict, List, Optional, Union
from typing_extensions import Literal

# Set up the shared logger
logger = setup_shared_logger()

# Define the state for the langgraph agent
class State(MessagesState):
    summary: str
    toolmsg: Annotated[list[ToolMessage], add]
    urls: tuple[str, List]

# Defining the Tavily web search tool that is available for use by agent
def web_search(query:str, topic:Literal['general','news']='general', 
               include_domains:List[str]=None, exclude_domains:List[str]=None,
               time_range:Literal['day','week','month','year']=None, max_results:int=5, relscore:float=0.7) -> str:
    """Sends query to Tavily web search API. Filter and return only the results from Tavily
    with relevance score of at least 0.7 and where raw content is not None."""
    try:
        web_search_tool = TavilySearch(topic=topic, search_depth='advanced', max_results=max_results, include_answer=False,
                                    include_raw_content=True)
        response = web_search_tool.invoke({"query":query,"include_domains":include_domains, "exclude_domains":exclude_domains, "time_range":time_range})
        # Extracts the url list
        urllist = response['results']
        # Updates the content dict with filtered url list, if applicable
        response['results'] = [item for item in urllist if float(item['score']) >= relscore and item.get('raw_content') is not None]
        return json.dumps(response)
    except (Exception, BaseException) as e:
        raise MyError(f"Error encountered while running Tavily search: {e}")

tools = [web_search]
llm_with_tools = Chat_OAI_llm.bind_tools(tools)

# Defining the components of the LangGraph chat agent
#1) Define the assistant node
def assistant(state:State):
    # Declare system message
    sys_msg = chatagent_sys_msg
    # Get summary of conversation if it exists
    summary = state.get("summary","")
    # If there is summary, then we add it to original system message
    if summary:
        # Add summary to original system message to get summary-infused system message
        sys_msg =  sys_msg + f" Here is a summary of the earlier conversation: <summary> {summary} </summary> "
    # Append system message to existing messages
    messages = [SystemMessage(content=sys_msg)] + state['messages']

    # Check if the latest message in the state is a ToolMessage
    if isinstance(state['messages'][-1], ToolMessage):
        # if so, extract the search urls from the content
            #url = [(state['messages'][-3].content, [item.get("url","") for item in json.loads(state['messages'][-1].content)['results']])]
        urls = (state['messages'][-3].content, json.loads(state['messages'][-1].content)['results'])
        toolmsg = [state['messages'][-1]]
    else:
        urls = ()
        toolmsg = []

    try:
        response = llm_with_tools.invoke(messages)
        return {"messages":response, "urls":urls, "toolmsg":toolmsg}
    except openai.APIError as e:
            raise MyError(f"Assistant node LLM API error: {e}")
    except (Exception, BaseException) as e:
            raise MyError(f"Assistant node general error: {e}")

#2) Define the summarisation node
def summarise_conversation(state:State):
    # extract text content in messages history
    messages = state['messages']
    content = " ".join([x.content for x in messages])
    # Check if token count of messages content history exceeds threshold if so,
    # proceed to summarise.
    try:
        if count_tokens(content) > 2048:
            # Get summary of conversation if it exists
            summary = state.get("summary","")
            if summary:
            # Case when summary already exists
                summary_message = (f" Summary of conversation history to date: {summary}. "
                                "Incorporate the content of the new messages above the summary into the existing conversation summary. "
                                "Cover ALL key points and main ideas presented, ensuring the flow is logical and consistent. "
                                "Then, provide a clear and consise summary of the updated conversation.")
            # Case when there is no summary yet
            else:
                summary_message = " Provide a clear and concise summary of the conversation above, covering ALL key points and main ideas presented. "
            # Add prompt to message history (except the last message). Not possible to do message[:-2] because Langgraph will raise error saying that the toolmsg is missing
            messages = messages[:-1] + [HumanMessage(content=summary_message)]  #cannot skip any message in between, e.g. ignore toolmessage, langgraph will give error
            response = llm_with_tools.invoke(messages)

            # Delete all message history, except the most recent one
            delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-1]]
            return {"summary": response.content, "messages": delete_messages}
        else:
            pass
    
    except openai.APIError as e:
            raise MyError(f"Summariser node LLM API error: {e}")
    except (Exception, BaseException) as e:
            raise MyError(f"Summariser node general error: {e}")

#3) Adding a conditional edge to determine whether to produce a summary
def should_continue(state: State) -> Literal["tools", "summarise_conversation"]:
    """Return the next node to execute."""
    messages = state["messages"]
    # If there is tool call by AI
    if isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "summarise_conversation"

#4) Build and compile langgraph agent
workflow = StateGraph(State)
# Define the nodes for the langgraph agent
workflow.add_node("assistant", assistant)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node(summarise_conversation)
# Define the edges for the langgraph agent
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges("assistant", should_continue)
workflow.add_edge("tools", "assistant")
workflow.add_edge("summarise_conversation", END)
# Define in-memory to store historical conversation. NB: memory is non-permanent
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)


def chatagent_response(query:str, id:str, langgraph:CompiledStateGraph=graph):
    """This function controls interaction with the chat agent. It takes in the user
    query and checks for malicious intent. If ok, the query is passed to the langgraph
    model to elicit LLM response."""

    # Safeguard the chatbot from malicious prompt
    # if prompt is deemed to be malicious, exit function with message
    if check_for_malicious_intent(client=Groq_client, model=Groq_model, user_message=query) == "Y":
        return ("Sorry, potentially malicious prompt detected. This request cannot be processed.","")
    else:
        try:
            # Specify a thread so that historical conversation within memory can be accessed
            config = {"configurable": {"thread_id": id}}
            input = [HumanMessage(content=f"<incoming-text>{query}</incoming-text>")]
            
            # Get LLM response
            output = langgraph.invoke({"messages": input},config)
            response = output['messages'][-1].content
            if len(output['urls'])>0 and query in output['urls'][0]:
                citation = output['urls'][1]
            else:
                citation = ""

            # Log into database
            conn = sqlite3.connect(f'{dbfolder}/data.db')
            cursor = conn.cursor()
            # Create table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agentlogs (
                    id TEXT,
                    log TEXT NOT NULL,
                    timestamp TEXt NOT NULL
                    )
                ''')
            # Insert data
            cursor.execute("INSERT INTO agentlogs (id, log, timestamp) VALUES (?, ?, ?)", (id,str(output),datetime.now().strftime("%d %b %Y, %H:%M:%S")))
            conn.commit()
            
            return (response, citation)
        
        except MyError as e:
            logger.error(f"Error while executing {os.path.basename(__file__)}: {e}")
        except sqlite3.Error as e:
            logger.error(f"Database connection error while executing {os.path.basename(__file__)}: {e}")
        except (Exception, BaseException) as e:
            logger.error(f"General error while executing {os.path.basename(__file__)}: {e}")
        
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
     pass