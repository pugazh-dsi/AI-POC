import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
FAISS_INDEX_DIR = BASE_DIR / "faiss_index"

DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR.mkdir(exist_ok=True)
FAISS_INDEX_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Local application database (provider config + API keys). Stays inside the repo
# under backend/data/ and is gitignored — it holds secrets.
DATABASE_FILE = DATA_DIR / "app.db"
SECRET_KEY_FILE = DATA_DIR / ".secret_key"

# Provider API keys are NOT read from the environment at runtime. They live
# encrypted in DATABASE_FILE and are managed through the Settings UI, so exactly
# one provider is active and the key never sits in a plaintext .env.
# The names below are read ONCE by app/store/bootstrap.py, which copies a legacy
# .env key into the database on first start and then never looks again.
LEGACY_ENV_KEYS = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}

# Optional master key for encrypting stored API keys. Generated on first run and
# written to SECRET_KEY_FILE when unset.
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}

EMBEDDING_MODEL = "text-embedding-ada-002"
LLM_MODEL = "gpt-3.5-turbo"  # default OpenAI chat model
DEFAULT_CHAT_PROVIDER = "openai"

# Generation settings shared by every chat provider
TEMPERATURE = 0.3
MAX_ANSWER_TOKENS = 1500
TOP_K_RESULTS = 8
SIMILARITY_THRESHOLD = 1.8  # Max L2 distance — ada-002 normalized vectors range 0-2

# Security & rate limiting
MAX_QUESTION_LENGTH = 1000
RATE_LIMIT_REQUESTS = 20  # Max requests per window
RATE_LIMIT_WINDOW = 60  # Window in seconds

# Embedding request batching — OpenAI caps inputs per embeddings request
EMBEDDING_BATCH_SIZE = 100

# Max tokens of document context sent to the LLM. gpt-3.5-turbo has a 16,385
# token window; this leaves room for the system prompt and a 1500-token answer.
MAX_CONTEXT_TOKENS = 12000
