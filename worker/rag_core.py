import os
import time
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")
if not google_api_key:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables")


def initialize_qdrant_connection():
    """Initialize Qdrant connection with retry logic"""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            client = QdrantClient(host=os.getenv("QDRANT_HOST"), port=6333)
            # Test connection by getting collections
            collections = client.get_collections()
            print(f"✅ Connected to Qdrant successfully on attempt {attempt + 1}")
            return client
        except Exception as e:
            print(
                f"❌ Qdrant connection attempt {attempt + 1}/{max_retries} failed: {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print("💥 Failed to connect to Qdrant after all retries")
                raise


# Initialize models and vector store
print("🔧 Initializing RAG components...")
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", google_api_key=google_api_key
)
qdrant_client = initialize_qdrant_connection()
vector_store = QdrantVectorStore(
    client=qdrant_client, collection_name="rag_collection", embedding=embedding_model
)
print("✅ RAG system initialized successfully!")

# RAG Chain setup with PromptTemplate
prompt_template = """
You are a helpful AI Assistant who answers user queries based on the available context retrieved from a PDF file.

You should only answer the user based on the following context. If you can't find the answer, state that you don't know, and don't make up an answer.
Also, navigate the user to the right page number to know more.

Context:
{context}

User Query:
{question}

Answer:
"""
PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_api_key)


def process_rag_query(query: str) -> str:
    # 1. Retrieval
    search_results = vector_store.similarity_search(query=query)

    # 2. Augmentation & Prompt Building
    context = "\n\n\n".join(
        [
            f"Page Content: {result.page_content}\nPage Number: {result.metadata['page_label']}\nFile Location: {result.metadata['source']}"
            for result in search_results
        ]
    )

    full_prompt = PROMPT.format(context=context, question=query)

    # 3. Generation
    # Your manual method
    response = llm.invoke(full_prompt)
    return response.content
