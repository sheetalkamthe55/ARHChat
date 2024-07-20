import argparse
import os
from langchain_community.vectorstores import Qdrant
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
import re
from tqdm import tqdm
from qdrant_client import QdrantClient

def clear_database(url="http://localhost:6333",collection_name="ARH_Tool",api_key=None):
    client = QdrantClient(url,api_key=api_key)
    client.delete_collection(collection_name)

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

def split_text(docs,chunksize=512,chunkoverlap=100):
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=chunksize,
        chunk_overlap=chunkoverlap,
        length_function=len,
    )
    documents = text_splitter.split_documents(docs)
    return documents

def embed_documents(documents, embed_model, url, api_key, collection_name):
    Qdrant.from_documents(documents, embed_model, url=url, api_key=api_key, prefer_grpc=True, collection_name=collection_name)

def main(url, pdf_folder_path , model_name, collection_name,chunksize,chunkoverlap,api_key = None):
    docs = extract_text_from_pdf(pdf_folder_path)
    docs_processed = split_text(docs,chunksize,chunkoverlap)
    for doc in docs_processed:
        doc.page_content = remove_emojis(doc.page_content)
    embed_model = setup_embeddings(model_name)
    embed_documents(docs_processed, embed_model, url, api_key, collection_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed PDF documents.")
    parser.add_argument("url", help="URL of the Vector Database")
    parser.add_argument("--pdf_folder_path", type=str, help="Path to read PDFs")
    parser.add_argument("--model_name", type=str, default='intfloat/e5-base-v2', help="Model name for embedding")
    parser.add_argument("--collection_name", type=str, default='ARH_Tool', help="Vector DB collection name")
    parser.add_argument("--chunksize", type=int, default=512, help="Chunk size for splitting text")
    parser.add_argument("--chunkoverlap", type=int, default=100, help="Chunk overlap for splitting text")
    parser.add_argument("--api_key", type=str, help="API key for authentication of vectordatabase (optional)", default=None)

    args = parser.parse_args()
    print("✨ Clearing Database")
    clear_database(args.url,args.collection_name,api_key=args.api_key)
    print("✨ Database Cleared")
    if not args.pdf_folder_path:
        # if not defined then take absolute path of the current directory + Content folder 
        args.pdf_folder_path = os.path.join(os.getcwd(), "Content")
    # check if content in the directory is present or not, if not then exit
    if not os.path.exists(args.pdf_folder_path):
        print("❌ Content folder not found.")
        exit(1)
    # if no pdf files are present in the folder then exit
    if not os.listdir(args.pdf_folder_path):
        print("❌ No PDFs found in the folder.")
        exit(1)
    main(args.url,args.pdf_folder_path,args.model_name,args.collection_name,args.chunksize,args.chunkoverlap,args.api_key)


# python3 embeddocs.py "http://localhost:6333" --reset "/Users/sheetalkamthe/Documents/Thesis/Documents/MicroservicesRefactoringApproaches" "intfloat/e5-base-v2" "ARH_Tool"