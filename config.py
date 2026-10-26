import os
from dotenv import load_dotenv

load_dotenv()

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "openai/gpt-oss-120b"
LLM_TEMPERATURE = 0

DATABASE_URL = os.getenv("DATABASE_URL")