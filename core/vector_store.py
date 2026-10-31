import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


COLLECTION_NAME= "video_transcript"

EMBEDDING_MODEL= "all-MiniLM-L6-v2"

def get_embeddings():
    return HuggingFaceEmbeddings(
        model= EMBEDDING_MODEL,
        model_kwargs={'device':'cpu'}
    )
    
def build_vectorstore(transcript):
    print("Building Vectorstore...")
    
    splitter= RecursiveCharacterTextSplitter(
        chunk_size= 500,
        chunk_overlap=50
    )    
    
    chunks= splitter.split_text(transcript)
    docs= [
    Document(
        page_content=chunk, metadata= {'chunk_index':i}
    )
    for i,chunk in enumerate(chunks)
    ]
    embeddings= get_embeddings()
    vector_store= Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME
    )
    return vector_store

def load_vectorstore():
    embeddings= get_embeddings()
    vector_store=Chroma(
        embedding_function= embeddings,
        collection_name= COLLECTION_NAME
    )
    return vector_store

def get_retriever(vector_store,k=4):
    retriever= vector_store.as_retriever(
        search_type= 'similarity',
        search_kwargs={'k':k}
    )
    return retriever