import streamlit_test as st

# region <--------- Streamlit App Configuration --------->
st.set_page_config(layout="wide", page_title="My Streamlit App")
# endregion <--------- Streamlit App Configuration --------->

st.title("Methodology")
st.write("""In **About Us**, an overview of the features for the three tools supporting the three use cases is presented. Here, the implementation details
         and data flows for each tool will be explained, accompanied by flow charts illustrating the process flow behind each tool.""")

st.subheader("ResaleStats")
st.image(
    "./pages/images/ResaleStats.drawio.png",
    caption="Flow chart showing overall process flow for ResaleStats",
    width=800,
)
st.write("""The 5 downloaded csv files were preprocesed before visualisation. The following details the data preprocessing steps. After preprocessing, visualisations
         , including filters, are created using standard streamlit functions.""")
data_transformation = """
**Data preprocessing and transformation**
1) *HDB Resale Price Index (1Q2009 = 100), Quarterly*
    - Read csv into pandas dataframe and filter for time period ('quarter') to start from 2004-Q1.
    - Keep the 'quarter' and 'index' fields, and store the dataframe as csv in the data folder.
2) *Median Resale Prices for Registered Applications by Town and Flat Type*
    - Read csv into pandas dataframe and filter for time period ('quarter') to start from 2020-Q1 (past 5 years).
    - Replace 'na' and '-' values in the price field with None.
    - Select the fields 'quarter', 'town', 'flat_type' and 'price', and store the dataframe as csv in the data folder.
3) *Resale flat prices based on registration date from Jan-2017 onwards*
    - Read csv into pandas dataframe and filter for time period ('month') to start from 2023-10 (past 12 months).
    - Remove redundant field - 'remaining_lease', and store the dataframe as csv in the data folder.
4) *CEA Salespersons’ Property Transaction Records (residential)*, *CEA Salesperson Information*
    - Read both csvs into pandas dataframes.
    - For the dataframe from the first csv:
        - Convert the 'transaction_date' field to python datetime format and filter to start from 2023-09-01
        - Remove records that are not associated with any salesperson.
        - Given the focus on HDB flat resale activity, remove other transaction activities by filtering for 'property_type' is HDB and 
          'transaction_type' is resale.
    - Left-join this processed dataframe with the dataframe from the second csv by the common key -> salesperson registration number, so
      as to get the real estate company that the salesperson is employed under
    - Select the relevant fields and store the joint dataframe as csv in the data folder.\n   
(For specific codes, refer to https://github.com/chuash/AIBootCamp2024_Capstone_final/blob/main/data_prep.py)
"""
st.write(data_transformation)
st.write("""In addition to interactive data analysis, users are also able to query data using words or natural language. The following details the implementation
         steps for the chat with data agent""")
st.image(
    "./pages/images/ResaleStatsChatAgent.drawio.png",
    caption="Flow chart showing process flow for chat with data agent",
    width=512,
)
agent = """
**Chat with data agent**
- Under the hood, the 'create_pandas_dataframe_agent' from *langchain_experimental.agents.agent_toolkits* is used, which in turn utilises OpenAI's 'gpt-4o-mini' model.
- When user inputs query, an OpenAI API call is made to ask gpt-4o-mini, suitably prompted with system message and few shot learning examples, to assess for
  potential prompt injection and malicious instructions. 
- If assessment is negative, then another OpenAI API call will be made to ask gpt-4o-mini, again suitably prompted with system message and few shot learning examples,to
  assess if the query is related to the underlying dataset. To help the LLM better assess, the dataset metadata is included in the system message to let the LLM understand
  the data it has access to. As added precaution against prompt injection, XML-like tags are used in both system and user messages.
- If assessment is positive, i.e. query is related to underlying dataset, then the 'create_pandas_dataframe_agent' is initialised, which will then access python repl tool
  to execute script on the underlying dataset. Queried results from the dataset are then passed to LLM to generate user response.
  
(For specific codes, refer to https://github.com/chuash/AIBootCamp2024_Capstone_final/blob/main/logics/agent.py)
"""
st.write(agent)

st.subheader("ResaleSearch")
st.image(
    "./pages/images/RAG.png",
    caption="Flow chart showing overall process flow for ResaleSearch",
    width=1024,
)
RAG = """
- Under the hood, *ResaleSearch* runs on Langchain's RAG techniques, OpenAI embeddings and OpenAI's LLM ('gpt-4o-mini'). A two-phase approach is adopted, Phase I prepares the knowledge to be
  persisted as Chroma vector store on disk. Phase II is the run-time scenario when user submits a query and the most relevant contexts are retrieved from the vector store
  to be passed on to the LLM to provide concise reply.\n

**Phase I**
- Scrape and load data from each of the three data sources into three langchain Document objects.
- For each of the Document object:
  - extract the metadata - 'source', 'title' and 'description'
  - clean up text content by removing non-breaking space, tabs, unnecessary whitespaces and/or redundant multiple newlines
  - filter away text content irrelevant to HDB resale knowledge
- Split and chunk the three Document objects using RecursiveCharacterTextSplitter , with chunk size 1000 characters, chunk overlap of 200 characters
- Splitted and chunked Document objects are then as Chroma vector store, on disk, at the data folder

(For specific codes, refer to https://github.com/chuash/AIBootCamp2024_Capstone_final/blob/main/logics/rag_preretrieval.py)

**Phase II**
- At run time, user has the option to either input query as it is or to make use of 'gpt-4o-mini' to help with query rewriting.
- Query rewriting involves a seperate OpenAI API call with a curated prompt to ask the LLM to review the original query and rephrase it in the way it feels would be able 
  to optimise retrieval quality of documents from the underlying vector database. To help the LLM better assess, keywords from the sub-topics of the knowledge base are 
  included in the curated prompt. To prevent the query rewriting functionality from being exploited, the user query is first checked to determine if it is potentially malicious.
  If not, the prompt asks the LLM to assess if the user query is related to the knowledge base. If somewhat relevant, the LLM proceeds with the query rewriting.
- User can choose whether to make use of the re-written query by copying and pasting the query into the form.
- Once user submits his query, the query is checked to determine if it is potentially malicious, if not malicious in nature, the Chroma vector store will be initialised from disk.
- Then the query will be run through a base retriever that provides maximal marginal relevance search, returning the top 8 contexts (max) that meet the relevance and diversity
  requirements.
- The contexts are then passed through a filter that uses embedding similarity to retain contexts that meet certain minimum similarity threshold.
- The filtered contexts are then passed to Cohere Reranker via API call to get the top 4 most relevant contexts.
- These contexts and the user query is then passed to 'gpt-4o-mini' to assess if it has sufficient information to answer user query. If the LLM assesses that it
  doesn't know the answer, or the retrieved contexts do not have the answer to the user query, it is prompted to say that "I am sorry but I don't know, please consider rephrasing or changing your query". 
  It has also been prompted not to make up an answer.

(For specific codes, refer to https://github.com/chuash/AIBootCamp2024_Capstone_final/blob/main/logics/rag_retrieval.py)
"""
st.write(RAG)

st.subheader("RenoChat")
st.image(
    "./pages/images/Renochat.drawio.png",
    caption="Flow chart showing overall process flow for Renochat",
    width=800,
)

renochat="""
- When the streamlit session first starts, Renochat's chat memory is initialised, as a session state variable, with its instruction system message.
- This system message tells the LLM the character that it is to role-play and that it should only reply to queries that it thinks are related to renovation.
- When user submits a query, the query is first checked to determine if it is potentially malicious, if not, the query is added to the chat memory.
- The updated chat memory is then passed to LLM ('gpt-4o-mini') to get response (capped at 300 tokens). If the LLM assesses that the query is unrelated to 
  renovation, it will reply something along the line that it is only supposed to respond to renovation related queries.
- The LLM response is then appended to chat memory.
- Check will be done to ensure that the accumulated chat history does not exceed the chat memory token threshold of 1024, if so, the entire chat history, excluding
  the initial instruction system message, is summarised (via OpenAI API call to 'gpt-4o-mini') to a maximum of 400 tokens. This summary is then recombined with the
  initial instruction system message.
- The chat memory is then updated accordingly.

(For specific codes, refer to https://github.com/chuash/AIBootCamp2024_Capstone_final/blob/main/logics/renochat.py)
"""
st.write(renochat)
