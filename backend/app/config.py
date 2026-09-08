import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
FAISS_INDEX_DIR = BASE_DIR / "faiss_index"

UPLOAD_DIR.mkdir(exist_ok=True)
FAISS_INDEX_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}

EMBEDDING_MODEL = "text-embedding-ada-002"
LLM_MODEL = "gpt-3.5-turbo"
TOP_K_RESULTS = 8
SIMILARITY_THRESHOLD = 1.8  # Max L2 distance — ada-002 normalized vectors range 0-2

# Security & rate limiting
MAX_QUESTION_LENGTH = 1000
RATE_LIMIT_REQUESTS = 20  # Max requests per window
RATE_LIMIT_WINDOW = 60  # Window in seconds
