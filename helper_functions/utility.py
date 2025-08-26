import streamlit_test as st
import hmac

def check_password():
    """This functions provides password protection for the
    streamlit app. Returns `True` if the user had the correct password,
    and user is thus allowed to access the streamlit app"""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            # DO NOT store the password.
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True
    # Show input for password.
    st.text_input(
        "Please enter password to proceed",
        type="password",
        on_change=password_entered,
        key="password",
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False
