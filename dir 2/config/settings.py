import os
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/free")
GENERATION_TEMPERATURE = 0.5
MAX_OUTPUT_TOKENS = 8192
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_NAME = EMBEDDING_MODEL
EMBEDDING_DEVICE = "cuda"

CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "chroma_db"
)
CHROMA_COLLECTION_NAME = "code_knowledge_base"

TOP_K_RESULTS = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

MAX_MEMORY_TURNS = 20
CODE_EXECUTION_TIMEOUT = 10

# ── Redis / Memurai Configuration ──
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cache TTLs (seconds)
CACHE_TTL_RETRIEVAL = 60 * 60 * 24       # 24 hours for retrieval cache
CACHE_TTL_RESPONSE = 60 * 60 * 12        # 12 hours for generator response cache
CACHE_TTL_MEMORY = 60 * 60 * 24 * 7      # 7 days for generator session memory

# Semantic Cache Configuration (Memurai vectorset)
SEMANTIC_CACHE_ENABLED = True
SEMANTIC_CACHE_THRESHOLD = 0.80
SEMANTIC_CACHE_KEY = "semantic_cache:prompts"
SEMANTIC_ANSWER_PREFIX = "semantic_cache:answer:"

# Generator defaults
MAX_REFINEMENT_LOOPS = 4

# Analyst Agent defaults
ANALYST_MAX_FEEDBACK_LOOPS = 2      # max round-trips back to the Retriever Agent
ANALYST_MAX_TOOL_STEPS = 6          # max tool-calling iterations per reasoning pass
ANALYST_MAX_FOLLOW_UP_QUERIES = 2   # max follow-up queries sent per feedback loop
ANALYST_EVIDENCE_CHAR_LIMIT = 1500  # chars of each evidence chunk shown to the LLM

# ── Image Upload & OCR Configuration ──
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
OCR_MIN_CONFIDENCE = 0.3
OCR_MAX_IMAGE_SIZE_MB = 20
IMAGE_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "uploads",
    "images",
)

# ── Report Generator Agent ──
REPORT_MAX_STEPS = 100  # LangGraph recursion limit (each design tool call uses steps)
REPORT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "reports",
)

# ── Voice & Speech-To-Text (STT) Configuration ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
STT_PROVIDER = os.getenv("STT_PROVIDER", "groq")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
AUDIO_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "uploads",
    "audio",
)
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac", ".aac"}
AUDIO_MAX_SIZE_MB = 25

# ── FastAPI Server Configuration ──
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
