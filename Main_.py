import sqlite3
import streamlit as st
from helper_functions.utility import check_password, dbfolder

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
def query_data(database = f'{dbfolder}/data.db'):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    return

# Divide real estate into 2 columns
col_topleft, col_topright = st.columns(2, gap="medium")

# on the left
with col_topleft:
    # line chart
    st.write("**1a. HDB Resale Price Index from 2004Q1 (index=100 in 2009Q1)**")

# on the right
with col_topright:
    # bar chart
    st.write("**1b. HDB Median Resale Prices($), by flat types**")