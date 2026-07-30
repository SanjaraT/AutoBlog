from langchain_groq import ChatGroq
from config import LLM_MODEL

llm = ChatGroq(model=LLM_MODEL)