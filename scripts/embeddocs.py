import argparse
import requests
import os
from langchain_community.vectorstores import Qdrant
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
import re
from tqdm import tqdm

def download_pdf(url, pdf_folder_path, api_key=None):
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        pdf_filename = url.split('/')[-1]
        pdf_path = os.path.join(pdf_folder_path, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        return pdf_path
    else:
        print(f"Failed to download PDF. Status code: {response.status_code}")
        return None

def extract_text_from_pdf(pdf_folder_path):
    documents = []
    loaders = [PyPDFLoader(os.path.join(pdf_folder_path, fn)) for fn in os.listdir(pdf_folder_path)]
    for loader in tqdm(loaders):
        try:
            documents.extend(loader.load())
        except:
            pass
    return documents

def remove_emojis(string):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', string)

def setup_embeddings(embedding_model_id):
    embed_model = HuggingFaceEmbeddings(model_name=embedding_model_id)
    return embed_model

def split_text(docs):
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=512,
        chunk_overlap=100,
        length_function=len,
    )
    documents = text_splitter.split_documents(docs)
    return documents

def embed_documents(documents, embed_model, url, api_key=None, collection_name="Default_Name"):
    Qdrant.from_documents(documents, embed_model, url=url, api_key=api_key, prefer_grpc=True, collection_name=collection_name)

def main(url, pdf_folder_path, model_name,collection_name, api_key=None):
    docs = extract_text_from_pdf(pdf_folder_path)
    docs = [remove_emojis(doc) for doc in docs]
    docs_processed = split_text(docs)
    embed_model = setup_embeddings(model_name)
    embed_documents(docs_processed, embed_model, url, api_key, collection_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed PDF documents.")
    parser.add_argument("url", help="URL to download the PDF from")
    parser.add_argument("pdf_folder_path", help="Path to save the downloaded PDF")
    parser.add_argument("model_name", help="Model name for embedding")
    parser.add_argument("collection_name", help="Vector DB collection name")
    parser.add_argument("--api_key", help="API key for authentication (optional)", default=None)

    args = parser.parse_args()

    main(args.url, args.pdf_folder_path, args.model_name,args.collection_name,args.api_key)


# python script.py "http://example.com/my.pdf" "/path/to/pdf/folder" "intfloat/e5-base-v2" "SampleCollection" --api_key "your_api_key_here"