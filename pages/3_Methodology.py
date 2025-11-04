import streamlit as st

st.set_page_config(layout="wide", page_title="CCS Merger Scanning Platform")


st.title("Methodology")
st.write("""...More information to be provided...""")
# Step 1 -> xxx_scrapper.py
# Step 2 -> gather all the scrapped news articles
# Step 3 -> run News_classifier.py to identify M&A related news articles and extract entities involved in merger
# Step 4 -> For each of the entities identified in each of the M&A news articles, conduct web search (where applicable) to answer MAu questions
# Step 5 -> Results from step 3 and 4 stored in database/data.db