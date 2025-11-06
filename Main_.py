import pandas as pd
import sqlite3
import streamlit as st
from helper_functions.utility import check_password, dbfolder, tablename

# Use form.sg for bug reporting, after that replace "http://www.help.com.sg" with the form.sg url
st.set_page_config(layout="wide", page_title="CCS Merger Scanning Platform", menu_items={
        'Report a bug': "http://www.help.com.sg",
        'About': "## The CCS Merger Scanning Platform by MAU and D2"})

st.title("CCS Merger Scanning Platform")

with st.expander("***Important Note***"):
    st.write(
    "This tool relies on AI-generated content, which may include inaccuracies or hallucinations. "
    "Users are advised to independently verify all information and not rely solely on these responses. "
    "Please cross-check important details through separate sources where necessary. ")

# Do not continue if check_password is not True.
if not check_password():
    st.stop()

# Function to query from database
@st.cache_data
def query_data(tablename:str, database:str = f'{dbfolder}/data.db'):
    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        sqlquery = f"SELECT * FROM {tablename} WHERE Extracted_Date = (SELECT MAX(Extracted_Date) FROM {tablename})"
        df = pd.read_sql_query(sqlquery, con=conn)
        return df
    except (Exception, BaseException, sqlite3.Error) as e:
        pass
    finally:
        if conn:
            conn.close()

# Load all relevant datasets
df_base = query_data(tablename=tablename)
df_query1 = query_data(tablename=f'{tablename}_websearch_query1')

# Divide real estate into 2 columns
col_topleft, col_topright = st.columns([0.7,0.3], gap="medium")

# on the left
with col_topleft:
    # line chart
    st.write("**Table 1....**")
    st.dataframe(df_base.head(10))

# on the right
with col_topright:
    # bar chart
    st.write("**1b. HDB Median Resale Prices($), by flat types**")