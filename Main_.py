import streamlit as st
from helper_functions.utility import check_password

# Use form.sg for bug reporting
st.set_page_config(layout="wide", page_title="CCS Merger Scanning Platform", menu_items={
        'Report a bug': "http://www.help.com.sg",
        'About': "## The CCS Merger Scanning Platform by MAU and D2"})

st.title("CCS Merger Scanning Platform")

with st.expander("*Disclaimer*"):
    st.write(
        """
    **IMPORTANT NOTICE**:
    This notice is to be updated
    """
    )

# st.cache_data.clear()

# Do not continue if check_password is not True.
if not check_password():
    st.stop()