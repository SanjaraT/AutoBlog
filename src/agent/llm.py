from langchain_groq import ChatGroq
from config import LLM_MODEL
from groq import RateLimitError

llm = ChatGroq(model=LLM_MODEL)


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