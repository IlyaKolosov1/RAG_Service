import os
import tempfile

import boto3

from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from config import S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET
from config import SERVICE_ACCOUNT_ID, PRIVATE_KEY, KEY_ID, FOLDER_ID

S3_ENDPOINT = "https://storage.yandexcloud.net"
S3_ACCESS_KEY = S3_ACCESS_KEY
S3_SECRET_KEY = S3_SECRET_KEY
S3_BUCKET = S3_BUCKET
S3_PREFIX = ""  # опционально — папка внутри бакета


def load_and_index_documents(local_paths):
    all_documents = []

    for path in local_paths:
        if path.endswith(".pdf"):
            loader = PyPDFLoader(path)
        elif path.endswith(".txt"):
            loader = TextLoader(path, encoding="utf-8")
        else:
            continue

        loaded_docs = loader.load()
        all_documents.extend(loaded_docs)

    valid_docs = [
        doc for doc in all_documents
        if hasattr(doc, 'page_content') and
           isinstance(doc.page_content, str) and
           doc.page_content.strip()
    ]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(valid_docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("./vectorstore_faiss")
    
    return vectorstore


def download_from_s3():
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name='ru-central1'
    )

    try:
        objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return None

    if 'Contents' not in objects:
        return load_and_index_documents([])
    print(objects)
    local_files = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for obj in objects['Contents']:
            key = obj.get('Key')
            print(key)
            if not key or not isinstance(key, str) or key.endswith('/'):
                continue

            size = obj.get('Size', 0)
            print(size)
            if size == 0:
                continue

            local_path = os.path.join(tmpdir, os.path.basename(key))
            print(local_path)
            try:
                s3.download_file(S3_BUCKET, key, local_path)
                if os.path.getsize(local_path) == 0:
                    continue
                local_files.append(local_path)
            except Exception as e:
                print(f"Ошибка скачивания {key}: {e}")
                continue

        return load_and_index_documents(local_files)


download_from_s3()
