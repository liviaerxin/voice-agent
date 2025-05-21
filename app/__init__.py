from dotenv import load_dotenv , find_dotenv
import os

load_dotenv(find_dotenv())

if (api_key:= os.getenv('OPENAI_API_KEY')):
    import openai
    OPENAI_API_KEY = api_key
    openai.api_key = api_key
    # print(openai.api_key)
