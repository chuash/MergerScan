import streamlit as st

st.set_page_config(layout="wide", page_title="CCS Merger Scanning Platform")

st.title("Tool Overview")

st.subheader("Objectives")
st.write("This platform aims to provide MAU officers, who have been tasked to keep a lookout for merger events, with a " \
"prelinminary classification of most probable merger related new articles. By doing so, it aims to reduce the number of news" \
"articles that officers have to go through, so that any time saving can be channeled to higher value merger research and analysis.")
st.subheader("Features")
st.write("There are four key modules - 1) News Collector, 2) News Classifier, 3) News Research, and 4) Chat Assistant")
st.markdown("""
            * 1) News Collector
                * This module comprises web-scraping scripts that are developed and customised for each predefined news source.
                * Scheduled to run at predefined intervals, the scripts will extract, from each news source, the following:
                  i) ***titles/headlines of news articles published after certain specified date***, 
                 ii) ***corresponding news article published dates***, 
                iii) ***name of news source***,
                 iv) ***extraction date***
                * Extracted information from each news source is then saved as individual CSV files in a temporary folder.<br><br>
            * 2) News Classifier
              * This module reads in all the news articles from the CSV files in the temporary folder, checks against the
                SQL database containing news from previous extractions, and removes any duplicated news articles.
              * The deduplicated news articles are then passed through selected LLM 
                (either ***meta-llama/llama-4-scout-17b-16e-instruct*** offered by **Groq** or ***GPT 4o-mini*** offered by **OpenAI**) 
                to let the LLM determine if the title/headlines of each news article is related to merger and acquisition, 
                and if so, extract the involved entities mentioned in the news article.
              * Response from the LLM for each news article is then parsed into table format and saved both as CSV file and the SQL
                database.<br><br>
            * 3) News Research
              * For each of the merger and acquisition related news article identified by the News Classifier, this module
                  * Conducts web research, based on predefined merger assessment queries, into the identified merger entities using **Perplexity**'s ***sonar-pro*** model with high context size.
                  * Parses the text response from **Perplexity API** through **OpenAI**'s ***GPT 4o-mini*** model to get the required structured response.
                  * Structured response is then parsed into table format and saved in SQL database.<br><br>
            * 4) Chat Assistant
              * This module is an add-on, with the intent to allow officers to conduct simple research without having to toggle to seperate browser tabs.
              * Under the hood, the assistant is powered by **OpenAI**'s ***GPT 4o-mini*** model with ephemeral memory capability.
              * More importantly, the assistant has access to **Tavily Web Search API**, this ensures the response is updated with current information and is not limited by the 
                underlying training data of the LLM.
            """,unsafe_allow_html=True)

