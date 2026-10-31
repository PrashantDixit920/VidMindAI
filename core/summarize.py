from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import os

def get_llm():
    return ChatGroq(
        model="openai/gpt-oss-120b",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3
    )
    
def split_transcript(transcript: str):
    splitter= RecursiveCharacterTextSplitter(
        chunk_size= 3000,
        chunk_overlap=200
    )    
    return splitter.split_text(transcript)

def summarize(transcript: str):
    llm= get_llm()
    map_prompt= ChatPromptTemplate.from_messages(
        [
            ("system","Summarize this portion of a meeting/video concisely"),
            ("human","{text}")
        ]
    )
    
    map_chain= map_prompt|llm|StrOutputParser()
    chunks= split_transcript(transcript=transcript)
    chunk_summaries= [map_chain.invoke(chunk) for chunk in chunks]
    combined_summary= "\n\n".join(chunk_summaries)
    
    combined_summary_prompt= ChatPromptTemplate.from_messages(
        [
            ("system","""
             You are an expert video transcript summarizer. Combine
             these partial summaries into one final
             professional summary in bullet points"""),
            ("human","{text}")
        ]
    )
    combined_summary_chain=(
        RunnablePassthrough()| RunnableLambda(lambda x:{"text":x})| combined_summary_prompt| llm| StrOutputParser()
    )
    return combined_summary_chain.invoke(combined_summary)

def generate_title(transcript: str):
    llm= get_llm()
    
    title_chain= RunnablePassthrough()| RunnableLambda(lambda x:{"text":x}) |ChatPromptTemplate.from_messages(
        [
            ("system","""
             Based on the video transcript generate a 
             short title for the video(max 8 words). Only
             return the title nothing else."""),
            ("human","{text}")
        ] )| llm|StrOutputParser()
            
    return title_chain.invoke(transcript[:2000])
           