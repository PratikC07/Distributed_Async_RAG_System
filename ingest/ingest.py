import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from pathlib import Path
import time
from qdrant_client.http.models import Distance, VectorParams
import sys

load_dotenv()

google_api_key = os.getenv("GEMINI_API_KEY")
if not google_api_key:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables")


# Initialize models and Qdrant client with retry logic
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", google_api_key=google_api_key
)


def connect_to_qdrant():
    max_retries = 10
    for attempt in range(max_retries):
        try:
            client = QdrantClient(url=f"http://{os.getenv('QDRANT_HOST')}:6333")
            # Test connection
            client.get_collections()
            print(f"Connected to Qdrant successfully on attempt {attempt + 1}")
            return client
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print("Failed to connect to Qdrant after all retries")
                sys.exit(1)


client = connect_to_qdrant()

# Define the collection name and file path
COLLECTION_NAME = "rag_collection"
PDF_FILE_PATH = Path("nodejs.pdf")


def ingest_documents():
    print("=" * 50)
    print("🚀 STARTING DOCUMENT INGESTION")
    print("=" * 50)
    try:
        # Load the document
        print(f"📄 Loading PDF from: {PDF_FILE_PATH}")
        if not PDF_FILE_PATH.exists():
            raise FileNotFoundError(f"PDF file not found: {PDF_FILE_PATH}")

        loader = PyPDFLoader(PDF_FILE_PATH)
        documents = loader.load()
        print(f"✅ Loaded {len(documents)} pages from PDF")

        # Split documents into chunks
        print("🔪 Splitting documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=400
        )
        chunks = text_splitter.split_documents(documents)
        print(f"✅ Created {len(chunks)} chunks for embedding")

        # --- 3. Check if data already exists ---
        print(f"🔍 Checking for collection '{COLLECTION_NAME}'...")
        if not client.collection_exists(collection_name=COLLECTION_NAME):
            print(f"📝 Collection '{COLLECTION_NAME}' not found. Creating it now...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
            )
            print(f"✅ Collection '{COLLECTION_NAME}' created.")
        else:
            print(f"✅ Collection '{COLLECTION_NAME}' already exists.")
            # Check if collection has data
            collection_info = client.get_collection(COLLECTION_NAME)
            points_count = collection_info.points_count
            print(f"📊 Found {points_count} existing points in collection")

            if points_count > 0:
                # Check if force re-ingestion is requested
                force_reingest = os.getenv("FORCE_REINGEST", "false").lower() == "true"
                if force_reingest:
                    print("⚠️  FORCE_REINGEST=true detected")
                    print("🗑️  Deleting existing collection...")
                    client.delete_collection(COLLECTION_NAME)
                    client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(
                            size=3072, distance=Distance.COSINE
                        ),
                    )
                    print("✅ Collection recreated. Proceeding with fresh ingestion...")
                else:
                    print("=" * 50)
                    print("🎯 DATA ALREADY EXISTS!")
                    print(f"✅ Collection already contains {points_count} vectors")
                    print("⏭️  Skipping ingestion process")
                    print("💡 To force re-ingestion, set FORCE_REINGEST=true")
                    print("🚀 Qdrant is ready for queries!")
                    print("=" * 50)
                    return  # Exit early - no need to re-ingest
            else:
                print("📝 Collection exists but is empty. Proceeding with ingestion...")

        # Now that the collection exists, initialize the LangChain QdrantVectorStore
        qdrant_client = QdrantVectorStore(
            client=client, collection_name=COLLECTION_NAME, embedding=embedding_model
        )

        # --- 4. Manually Batch and Store in Qdrant with a delay ---
        print("🔄 Storing chunks in Qdrant with rate-limiting...")
        print(f"📊 Batch size: 10 chunks, Delay: 30 seconds between batches")
        BATCH_SIZE = 10  # Reduced batch size
        DELAY_SECONDS = 30  # Increased delay

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

            print(
                f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)..."
            )

            max_retries = 3
            for retry in range(max_retries):
                try:
                    qdrant_client.add_documents(batch)
                    print(f"✅ Batch {batch_num} complete!")
                    break
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        wait_time = (retry + 1) * 60  # Wait 1, 2, 3 minutes
                        print(
                            f"⚠️  API quota exceeded. Waiting {wait_time} seconds before retry {retry + 1}/{max_retries}..."
                        )
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Error in batch {batch_num}: {e}")
                        if retry == max_retries - 1:
                            raise
                        time.sleep(10)

            if i + BATCH_SIZE < len(chunks):  # Don't sleep after the last batch
                print(f"⏳ Waiting {DELAY_SECONDS} seconds before next batch...")
                time.sleep(DELAY_SECONDS)

        print("=" * 50)
        print("🎉 INGESTION COMPLETE!")
        print(f"✅ Successfully indexed {len(chunks)} chunks to Qdrant")
        print("🚀 Qdrant is ready for queries!")
        print("=" * 50)

    except Exception as e:
        print("=" * 50)
        print(f"❌ INGESTION FAILED: {e}")
        print("=" * 50)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    ingest_documents()
