import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "20"))
LEXICAL_TOP_K = int(os.getenv("LEXICAL_TOP_K", "20"))
FINAL_TOP_K = int(os.getenv("FINAL_TOP_K", "5"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen2.5:7b")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "20"))
ARXIV_POLL_SECONDS = int(os.getenv("ARXIV_POLL_SECONDS", "60"))

PAPERS_DIR = Path(os.getenv("PAPERS_DIR", "data/papers"))
PAPERS_DIR.mkdir(parents=True, exist_ok=True)

AI_CATEGORIES = {
    "cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO",
    "cs.NE", "cs.IR", "cs.MA", "stat.ML"
}

AI_TERMS = {
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "transformer", "large language model", "llm",
    "language model", "computer vision", "natural language processing",
    "nlp", "retrieval augmented generation", "rag", "agent", "agents",
    "multimodal", "reinforcement learning", "generative ai",
    "diffusion model", "embedding", "foundation model"
}
