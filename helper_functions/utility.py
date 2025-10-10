import logging, os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from openai import OpenAI

if not load_dotenv(".env"):
    pass

Groq_model = os.getenv("GROQ_MODEL_NAME")
OAI_model = os.getenv("OPENAI_MODEL_NAME")  
Groq_client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
OAI_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
Perplexity_client = OpenAI(api_key=os.getenv("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai")
                           #max_retries=os.getenv("PERPLEXITY_MAX_RETRIES"), timeout=os.getenv("PERPLEXITY_TIMEOUT"))
                           

# Setting up custom exception class
class MyError(Exception):
    def __init__(self, value):
        self.value = value

    # Defining __str__ so that print() returns this
    def __str__(self):
        return self.value


# Setting up logger
def setup_shared_logger(log_file_name="application.log"):
    """
    Sets up a shared logger instance for the entire application.
    """
    # Create the logger
    logger = logging.getLogger('shared_app_logger')
    # Set the desired logging level
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if setup_shared_logger is called multiple times
    if not logger.handlers:
        # Create a file handler
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setLevel(logging.INFO)

        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        logger.addHandler(file_handler)

    return logger

# Function to check streamlit log in password
#def check_password():
#    """This functions provides password protection for the
#    streamlit app. Returns `True` if the user had the correct password,
#    and user is thus allowed to access the streamlit app"""

#    def password_entered():
#        """Checks whether a password entered by the user is correct."""
#        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
#            st.session_state["password_correct"] = True
#            # DO NOT store the password.
#            del st.session_state["password"]
#        else:
#            st.session_state["password_correct"] = False

#    # Return True if the password is validated.
#    if st.session_state.get("password_correct", False):
#        return True
#    # Show input for password.
#    st.text_input(
#        "Please enter password to proceed",
#        type="password",
#        on_change=password_entered,
#        key="password",
#    )
#    if "password_correct" in st.session_state:
#        st.error("😕 Password incorrect")
#    return False
