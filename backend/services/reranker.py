from sentence_transformers import CrossEncoder
from backend.services.config import RERANKER_MODEL

_model = None

def load_reranker_model():
    global _model
    if _model is None:
        print(f"Loading reranker: {RERANKER_MODEL}")
        _model = CrossEncoder(RERANKER_MODEL)
        print("Reranker loaded.")
    return _model

def rerank_chunks(query, results, top_k=5):
    if not results:
        return []

    model = load_reranker_model()
    pairs = [(query, r.get("chunk_text", "")) for r in results]
    scores = model.predict(pairs, show_progress_bar=False)

    for result, score in zip(results, scores):
        result["rerank_score"] = float(score)

    return sorted(
        results,
        key=lambda x: x["rerank_score"],
        reverse=True
    )[:top_k]
