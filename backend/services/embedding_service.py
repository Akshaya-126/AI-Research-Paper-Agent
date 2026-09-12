from sentence_transformers import SentenceTransformer
from backend.services.config import EMBEDDING_MODEL

_model = None

def load_embedding_model():
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print("Embedding model loaded.")
    return _model

def generate_embeddings(texts):
    model = load_embedding_model()
    if not texts:
        return []
    return model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    )
