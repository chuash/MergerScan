import streamlit_test as st
from helper_functions.utility import check_password

# region <--------- Streamlit App Configuration --------->
st.set_page_config(layout="wide", page_title="HDB Resale Tips App")
# endregion <--------- Streamlit App Configuration --------->

st.title("HDB Resale Tips App")

with st.expander("*Disclaimer*"):
    st.write(
        """

    **IMPORTANT NOTICE**:

    This web application is a prototype developed for **educational purposes only**. The information provided here is **NOT intended for real-world usage** and should not be relied upon for making any decisions, especially those related to financial, legal, or healthcare matters.

    **Furthermore, please be aware that the LLM may generate inaccurate or incorrect information. You assume full responsibility for how you use any generated output.**

    Always consult with qualified professionals for accurate and personalized advice.

    """
    )

# st.cache_data.clear()

# Do not continue if check_password is not True.
if not check_password():
    st.stop()



def form_callback():
    st.write(st.session_state.my_slider)
    st.write(st.session_state.my_checkbox)

def slider_callback():
    st.write("My slider1 has value of", st.session_state.my_slider1)

with st.form(key='my_form'):
    slider_input = st.slider('My slider', 0, 10, 5, key='my_slider')
    checkbox_input = st.checkbox('Yes or No', key='my_checkbox')
    submit_button = st.form_submit_button(label='Submit', on_click=form_callback)

st.write("My slider has value of",st.session_state.my_slider, "\n\n")
st.write("My checkbox has value of",st.session_state.my_checkbox, "\n\n")
st.slider('My slider1', 1, 10, 7, key='my_slider1', on_change=slider_callback)
#st.write("My slider1 has value of", st.session_state.my_slider1)