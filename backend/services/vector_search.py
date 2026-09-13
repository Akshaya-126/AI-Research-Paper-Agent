import re

from backend.database.supabase_database import supabase
from backend.services.config import FINAL_TOP_K


def normalize_paper_id(paper_id):
    paper_id = paper_id.strip()

    if "/abs/" in paper_id:
        paper_id = paper_id.split("/abs/")[-1]

    elif "/pdf/" in paper_id:
        paper_id = paper_id.split("/pdf/")[-1]
        paper_id = paper_id.removesuffix(".pdf")

    return paper_id.rstrip("/")


def extract_query_terms(query):
    stopwords = {
        "what", "when", "where", "which", "who", "why", "how",
        "was", "were", "are", "is", "the", "a", "an", "and", "or",
        "of", "to", "in", "on", "for", "with", "from", "by", "about",
        "does", "do", "did", "has", "have", "had", "this", "that",
        "these", "those", "it", "its", "they", "their", "be", "been",
        "being", "can", "could", "would", "should"
    }

    words = re.findall(r"[a-zA-Z0-9]+", query.lower())

    return [
        word
        for word in words
        if word not in stopwords and len(word) > 2
    ]


def lexical_search(query, paper_id, top_k=20):
    """
    Lightweight retrieval for Render.

    Uses Supabase PostgreSQL full-text search.
    No embedding model is loaded.
    No CrossEncoder is loaded.
    """

    paper_id = normalize_paper_id(paper_id)

    terms = extract_query_terms(query)

    if not terms:
        return []

    candidates = {}

    # Search individual important terms.
    # This is more tolerant than requiring every query term
    # to occur in the same chunk.
    for term in terms:

        response = supabase.rpc(
            "search_paper_chunks_lexical",
            {
                "search_query": term,
                "match_count": top_k,
                "target_paper_id": paper_id,
            },
        ).execute()

        for item in response.data or []:

            chunk_id = item["id"]

            if chunk_id not in candidates:
                candidates[chunk_id] = dict(item)

            old_score = candidates[chunk_id].get(
                "lexical_score",
                0,
            )

            new_score = item.get(
                "lexical_score",
                0,
            )

            candidates[chunk_id]["lexical_score"] = (
                old_score + new_score
            )

    results = list(candidates.values())

    results.sort(
        key=lambda x: x.get("lexical_score", 0),
        reverse=True,
    )

    return results[:top_k]


def retrieve_best_chunks(
    query,
    paper_id,
    final_top_k=FINAL_TOP_K,
):
    """
    Lightweight Render-compatible retrieval.

    Retrieval is based on PostgreSQL full-text search.
    Gemini performs the final reasoning over the retrieved
    paper sections.
    """

    results = lexical_search(
        query,
        paper_id,
        top_k=max(final_top_k * 4, 20),
    )

    return results[:final_top_k]


if __name__ == "__main__":

    paper_id = "2609.11916v1"

    questions = [
        "What is the main contribution?",
        "What are the limitations?",
        "What is the methodology?",
        "What are the experiments?",
    ]

    for question in questions:

        print("\n" + "=" * 80)
        print(question)
        print("=" * 80)

        results = retrieve_best_chunks(
            question,
            paper_id,
            final_top_k=5,
        )

        if not results:
            print("\nNo relevant chunks found.")
            continue

        print("\nRetrieved chunks:")

        for i, chunk in enumerate(results, 1):

            print(
                f"{i}. "
                f"chunk={chunk['chunk_index']} "
                f"section={chunk.get('section')} "
                f"pages="
                f"{chunk.get('page_start')}-"
                f"{chunk.get('page_end')} "
                f"score="
                f"{chunk.get('lexical_score', 0):.4f}"
            )