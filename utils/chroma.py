# chroma.py
import streamlit as st
import os
import re
from pathlib import Path

import chromadb
from chromadb.config import Settings
from llama_index import (
    GPTChromaIndex,
    LangchainEmbedding,
    LLMPredictor,
    PromptHelper,
    OpenAIEmbedding,
)
from utils.model_settings import (
    sentenceTransformers,
    get_service_context,
    get_embed_model,
)

import logging

from utils.qa_template import QA_PROMPT


def get_collection_index_path(collection):
    return f'./data/{collection}-index.json'


# INDEX_PATH = './data/chroma_index.json'
PERSIST_DIRECTORY = './data/chromadb'

service_context = get_service_context()


@st.cache_resource
def create_chroma_client():
    return chromadb.Client(
        Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=PERSIST_DIRECTORY,
            anonymized_telemetry=False,
        )
    )


def get_chroma_collection(collection_name):
    client = create_chroma_client()
    try:
        return client.get_collection(collection_name)
    except Exception as e:
        logging.error(f"Failed to get collection '{collection_name}': {e}")
        return None


@st.cache_resource
def load_chroma_index(collection):
    collection_index_path = get_collection_index_path(collection)
    _chroma_collection = get_chroma_collection(collection)
    if Path(collection_index_path).exists():
        index = GPTChromaIndex.load_from_disk(
            collection_index_path,
            chroma_collection=_chroma_collection,
            service_context=service_context,
        )
        logging.info('Index loaded for collection ' + collection)
    else:
        index = None
    return index


# def build_chroma_index(documents, collection, reindex=False, chunk_size_limit=512, model_name='sentence-transformers/all-MiniLM-L6-v2'):
#     collection_index_path = get_collection_index_path(collection)
#     chroma_client = create_chroma_client()
#     if reindex is True:
#         chroma_client.delete_collection(collection)
#         os.remove(get_collection_index_path(collection))
#     _chroma_collection = chroma_client.get_or_create_collection(collection)
#     index = None
#     index = GPTChromaIndex.from_documents(documents, chroma_collection=_chroma_collection,
#                         service_context=get_service_context(embed_model=get_embed_model(model_name), chunk_size_limit=chunk_size_limit)
#                         )
#     index.save_to_disk(collection_index_path)
#     chroma_client.persist()


def create_or_refresh_chroma_index(
    documents,
    collection,
    reindex=False,
    chunk_size_limit=512,
    model_name='sentence-transformers/all-MiniLM-L6-v2',
):
    collection_index_path = get_collection_index_path(collection)
    chroma_client = create_chroma_client()
    if not Path(collection_index_path).exists() or reindex is True:
        if reindex is True:
            chroma_client.delete_collection(collection)
            os.remove(get_collection_index_path(collection))
        _chroma_collection = chroma_client.get_or_create_collection(collection)
        index = None
        index = GPTChromaIndex.from_documents(
            documents,
            chroma_collection=_chroma_collection,
            service_context=get_service_context(
                embed_model=get_embed_model(model_name=model_name),
                chunk_size_limit=chunk_size_limit,
            ),
        )
        index.save_to_disk(collection_index_path)
        chroma_client.persist()
    else:
        refresh_chroma_index(documents, collection)


def refresh_chroma_index(documents, collection):
    collection_index_path = get_collection_index_path(collection)
    index = load_chroma_index(collection)
    logging.info('refreshing collection ' + collection)
    refreshed_docs = index.refresh(documents)
    index.save_to_disk(collection_index_path)
    chroma_client = create_chroma_client()
    chroma_client.persist()
    return refreshed_docs


def query_index(
    query_str,
    collection,
    similarity_top_k=5,
    response_mode='compact',
    streaming=False,
    model_name=sentenceTransformers.OPTION1.value,
):
    index = None
    _chroma_collection = get_chroma_collection(collection)
    index = load_chroma_index(collection)
    return index.query(
        query_str,
        "embedding",
        similarity_top_k=similarity_top_k,
        response_mode=response_mode,  # default, compact, tree_summarize, no_text
        service_context=get_service_context(
            embed_model=get_embed_model(model_name=model_name)
        ),
        # chroma_collection=_chroma_collection,
        text_qa_template=QA_PROMPT,
        verbose=True,
        use_async=True,
        streaming=streaming,
    )


def persist_chroma_index():
    chroma_client = create_chroma_client()
    chroma_client.persist()


def generate_chroma_compliant_name(name: str) -> str:
    # Replace non-alphanumeric characters with underscores
    new_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name)
    # Replace consecutive periods with a single underscore
    new_name = re.sub(r"\.{2,}", "_", new_name)
    # Ensure the name starts and ends with an alphanumeric character
    if not new_name[0].isalnum():
        new_name = "a" + new_name[1:]
    if not new_name[-1].isalnum():
        new_name = new_name[:-1] + "a"
    # Truncate or pad the name to be between 3 and 63 characters
    new_name = new_name[:63]
    while len(new_name) < 3:
        new_name += "0"

    return new_name
