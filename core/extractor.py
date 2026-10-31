from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.summarize import get_llm


def build_chain(system_prompt: str):
    llm= get_llm()
    return (RunnablePassthrough()| RunnableLambda(lambda x:{"text":x})|ChatPromptTemplate.from_messages(
        [
            ("system",system_prompt),
            ("human","{text}")
        ]
    )|llm|StrOutputParser())
    
def extract_action_items(transcript: str):
    chain= build_chain("""
                       You are an expert meeting analyst. From
                       the meeting transcript, extract all action items.
                       For each provide:\n
                       -Task Description\n
                       -Owner(who is responsible)\n
                       -Deadline(if mentioned else specify Not mentioned)\n\n
                       Format as a numbered list. If none found say No action
                       items found""")
    return chain.invoke(transcript)

def extract_key_decisions(transcript: str) -> str:
    chain = build_chain(
        "You are an expert meeting analyst. From the meeting transcript, "
        "extract all key decisions made. Format as a numbered list. "
        "If none found say 'No key decisions found.'"
    )
    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:
    chain = build_chain(
        "From the meeting transcript, extract all unresolved questions "
        "or topics needing follow-up. Format as a numbered list. "
        "If none found say 'No open questions found.'"
    )
    return chain.invoke(transcript)    