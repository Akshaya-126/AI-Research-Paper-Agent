from backend.services.paper_retriever import is_ai_relevant

def classify_paper(result) -> bool:
    """
    Final lightweight relevance gate.

    Category is the candidate signal; title and abstract are semantic
    evidence. This function is intentionally paper-independent.
    """
    return is_ai_relevant(result)
