import json, os
import pandas as pd
import sqlite3, uuid
import streamlit as st
from helper_functions.utility import check_password, dbfolder, tablename, setup_shared_logger
from helper_functions.prompts import Query1_user_input, Query2_user_input, Query3_user_input
from Chat_agent import chatagent_response

st.set_page_config(layout="wide", page_title="CCS Merger Scanning Platform", menu_items={
        'Report a bug': "https://form.gov.sg/690d973dff46ce8978dcd393",
        'About': "## The CCS Merger Scanning Platform by MAU and D2"})

# Set up the shared logger
logger = setup_shared_logger()

st.title("CCS Merger Scanning Platform")

with st.expander("***Important Note***"):
    st.write(
    "This tool relies on AI-generated content, which may include inaccuracies or hallucinations. "
    "Users are advised to independently verify all information and not rely solely on these responses. "
    "Please cross-check important details through separate sources where necessary. ")

# Do not continue if check_password is not True.
if not check_password():
    st.stop()

# Setting up variables in session state
if 'merger_filter_button_clicked' not in st.session_state:
    st.session_state.merger_filter_button_clicked = False

if 'userid' not in st.session_state:
    st.session_state.userid = str(uuid.uuid4().hex)

@st.cache_data
def query_data(tablename:str, published_date:str=None, database:str = f'{dbfolder}/data.db'):
    """Function to query from database"""
    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        if published_date is None:
            sqlquery = f"SELECT * FROM {tablename} WHERE Extracted_Date = (SELECT MAX(Extracted_Date) FROM {tablename}) ORDER BY Published_Date DESC"
        else:
            sqlquery = f"SELECT * FROM {tablename} WHERE Published_Date >= '{published_date}' ORDER BY Published_Date DESC"
        #print(sqlquery)
        df = pd.read_sql_query(sqlquery, con=conn)
        return df
    except (Exception, BaseException, sqlite3.Error) as e:
        logger.error(f"Error while executing {os.path.basename(__file__)} and querying from the database table named {tablename}: {e}")
    finally:
        if conn:
            conn.close()

def click_merger_filter():
    """Callback function to update session state when the button is clicked."""
    st.session_state.merger_filter_button_clicked = True

def reset_merger_filter():
    """Callback function to update session state when the button is clicked."""
    st.session_state.merger_filter_button_clicked = False

# Divide real estate into 2 columns
col_topleft, col_topright = st.columns([0.65,0.35], gap="small",border=True)

# on the left
with col_topleft:
    # Divide real estate into 3 columns
    left_left, left_centre, left_right = st.columns([0.45,0.4,0.15], gap="small")
    with left_left:
        st.date_input("Filter for news articles published after [date]", value=None, key='published_date_filter', format="YYYY-MM-DD")
    with left_centre:
        st.button("Filter for merger-related news", key='merger_filter', help='Click to filter for merger-related news classified by AI', type="secondary", on_click=click_merger_filter)
    with left_right:
        st.button("Reset", key='reset_merger_filter', help='Click to see all news', type="primary", on_click=reset_merger_filter)
    
    st.divider()

    st.write("### Table 1: News articles")

    # Querying from database table 'news'
    df_base = query_data(tablename=tablename, published_date=st.session_state.published_date_filter)
    # Adding a 'Selected' column for selection
    df_base["Selected"] = False
    # If the "Filter for merger-related news" button is clicked, filter accordingly
    if st.session_state.merger_filter:
        df_base = df_base[df_base['Merger_Related'] == 'true']
    # If the value of the cell in "Merger_Related" column is true, highlight cell in green
    df_base_style = df_base.style.map(lambda x: f"background-color: {'green' if x=='true' else ''}", subset='Merger_Related')
    edited_df = st.data_editor(
                    df_base_style,
                    column_order= ('Selected','Published_Date', 'Extracted_Date','Merger_Related', 'Text','Merger_Entities','Reasons','Source'),
                    column_config={"Selected": st.column_config.CheckboxColumn(
                        label="Select",
                        help="Select only one news article at a time to view research",
                        pinned=True,
                        default=False,
                        )
                    },
                    hide_index=None,
                    disabled=['Merger_Related'],
                    num_rows="fixed",
                    key='news_table'
                )
    st.write("***Please only select one news article, at a time, to view research details***")

    selected_data = edited_df[edited_df["Selected"]]
    # if the particular record is selected by clicking on one of the checkboxes
    if not selected_data.empty:
        text = selected_data['Text'].values[0]
        published = selected_data['Published_Date'].values[0]
        extracted = selected_data['Extracted_Date'].values[0]
        source = selected_data['Source'].values[0]
        df_query1 = query_data(tablename=f'{tablename}_websearch_query1', published_date=st.session_state.published_date_filter)
        df_query1 = df_query1.loc[(df_query1['Published_Date']==published) & (df_query1['Extracted_Date']==extracted) & (df_query1['Source']==source) & (df_query1['Text']==text)]
        # If there is matching records
        if len(df_query1)>0:
                # When there are other queries, query the other tables accordingly and then merge to get df_query_combined. For now, to simulate df_query_combined, do a .copy()
                df_query_combined = df_query1.copy()
                merged_df = pd.merge(df_base, df_query_combined, on=['Published_Date','Source','Extracted_Date','Text'], how='inner')#.drop(['Reasons','Source','Selected','Merger_Related'], axis=1, inplace=False)
    
    st.write("### Table 2: Research related to merger news")
        
    col_bottomleft, col_bottomright = st.columns([0.2,0.8], gap="small")
    if not selected_data.empty and len(df_query1)>0:
        with col_bottomleft:
                query_option = st.radio(
                                "Select to view the research details",
                                [field for field in df_query1.columns if "Query" in field],
                                key='query_options'
                                )
            
        with col_bottomright:
            st.write("**Research Question:**")
            st.write(eval(f"{query_option}_user_input"))
            st.write("**Research Results:**")
            st.dataframe(data=pd.DataFrame(json.loads(eval(merged_df[query_option].values[0])[2])['response']),key='research_results_table')
            st.write("**Web Search Urls:**")
            st.dataframe(data=pd.DataFrame(eval(merged_df[query_option].values[0])[1], columns=['Urls']),
                         column_config={"Urls": st.column_config.LinkColumn(    
                                        help="Click to visit the web search urls")}, key='url_table') 
            

# on the right
with col_topright:
    form = st.form(key="chat_assistant")
    form.markdown("#### Your Friendly AI Chat Assistant")

    user_prompt_chat = form.text_area(
    """Post your queries here and the assistant\
    will provide you with curated answers sourced from internet, where applicable""",
    height=200,
    key="chat_assistant_text")

    if form.form_submit_button("Submit"):
        st.toast(f"Query Submitted - {user_prompt_chat}")
        with st.spinner("Fetching results..."):
            response, citation = chatagent_response(query=user_prompt_chat, id=st.session_state.userid)
            st.write(response)
            if len(citation) > 0:
                st.write(citation)
