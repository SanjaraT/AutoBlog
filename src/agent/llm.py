# from langchain_openai import ChatOpenAI
# from config import OPENROUTER_API_KEY, LLM_MODEL


# llm = ChatOpenAI(
#     model=LLM_MODEL,
#     api_key=OPENROUTER_API_KEY,
#     base_url="https://openrouter.ai/api/v1",
# )

# def with_groq_retry(runnable):
#     return runnable.with_retry(stop_after_attempt=3)

from langchain_groq import ChatGroq
from config import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from groq import RateLimitError

llm = ChatGroq(
    model=LLM_MODEL,
    api_key=GROQ_API_KEY,
    temperature=LLM_TEMPERATURE,
)


def with_groq_retry(runnable):
    """
    Wrap any runnable (plain llm, or llm.with_structured_output(...)) with
    automatic retry on Groq's rate-limit errors. Apply this AFTER binding
    structured output, not on the raw llm object, since with_retry() returns
    a generic RunnableRetry that no longer exposes with_structured_output().
    """
    return runnable.with_retry(
        retry_if_exception_type=(RateLimitError,),
        wait_exponential_jitter=True,
        stop_after_attempt=5,
    )