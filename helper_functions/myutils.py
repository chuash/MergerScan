import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from openai import OpenAI
from pydantic import BaseModel


# load environment variables
load_dotenv()
Groq_model = os.getenv("GROQ_MODEL_NAME")
OAI_model = os.getenv("OPENAI_MODEL_NAME")
Gemini_model = os.getenv("GEMINI_MODEL_NAME")
Groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
OAI_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
Gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
Ollama_client =  OpenAI(base_url = 'http://localhost:11434/v1',
                        api_key='ollama') # required, but unused


class Response(BaseModel):
    Explanation: str
    Answer: str


class MyError(Exception):
    def __init__(self, value):
        self.value = value

    # Defining __str__ so that print() returns this
    def __str__(self):
        return self.value
    
def llm_response(client: Groq | OpenAI , sys_msg: str, user_qn: str,
              model: str = "llama-3.3-70b-versatile",
              temperature: int = 0, top_p: int = 1, max_tokens: int = 1024, is_json: bool=True) -> str:
    
    if is_json:
      json_output={
           "type": "json_schema",
           "json_schema":{
                "schema": {
                    "type": "object",
                    "properties": {
                        "Explanation": {
                            "type": "string",
                            "description": "logical analysis of question with reasoning"
                        },
                        "Answer": {
                            "type": "string",
                            "description": "Only either True or False, determined based on analysis in explanation. No other text allowed",
                            "enum": ["True", "False"]
                        }
                    },
                    "required": ["Explanation", "Answer"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    else:
      json_output=None

    chat_completion = client.chat.completions.create(
        messages=[
            # Sets system message. This sets the behavior of the
            # assistant and can be used to provide specific instructions for
            # how it should behave throughout the conversation.
            {
             "role": "system",
             "content": sys_msg
            },
            # Set a user message for the assistant to respond to.
            {
             "role": "user",
             "content": f"<question_list> {user_qn} </question_list>",
            }
        ],

        # The language model which will generate the completion.
        model=model,

        # Controls randomness: lowering results in less random completions.
        # As the temperature approaches zero, the model will become deterministic
        # and repetitive.
        temperature=temperature,

        # The maximum number of tokens to generate. Requests can use up to
        # 32,768 tokens shared between prompt and completion.
        max_completion_tokens=max_tokens,

        # Controls diversity via nucleus sampling: 0.5 means half of all
        # likelihood-weighted options are considered.
        top_p=top_p,

        # A stop sequence is a predefined or user-specified text string that
        # signals an AI to stop generating content, ensuring its responses
        # remain focused and concise. Examples include punctuation marks and
        # markers like "[end]".
        stop=None,

        # If set, partial message deltas will be sent.
        stream=False,
        response_format = json_output
        #response_format={"type":"json_object"}
    )

    return chat_completion.choices[0].message.content


def gemini_response(client: genai.Client, sys_msg: str, user_qn: str, 
                    model: str = "gemini-2.0-flash-lite",
                    temperature: int = 0, top_p: int = 1, max_tokens: int = 1024, is_json: bool=True) -> str:
    
    if is_json:
        response_mime_type = 'application/json'
        response_schema = Response
    else:
        response_mime_type = None
        response_schema = None

    chat_completion = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(
                            system_instruction=f"{sys_msg}, exclude the original question, the preceding 'json' term and triple backticks in your response",
                            maxOutputTokens = max_tokens,
                            temperature = temperature,
                            response_mime_type= response_mime_type,
                            response_schema= response_schema,
                            topP = top_p),
                contents=f"""<question_list> {user_qn} </question_list>"""
    )

    return chat_completion.text

