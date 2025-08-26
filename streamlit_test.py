import streamlit_test as st
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