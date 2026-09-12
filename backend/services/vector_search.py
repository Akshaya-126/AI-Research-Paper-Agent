import re

from backend.database.supabase_database import supabase
from backend.services.embedding_service import load_embedding_model
from backend.services.config import (
    VECTOR_TOP_K,
    LEXICAL_TOP_K,
    FINAL_TOP_K,
)
from backend.services.reranker import rerank_chunks


def normalize_paper_id(paper_id):
    """
    Convert any supported arXiv identifier into the database format.

    Supported:
        2609.11929v1
        https://arxiv.org/abs/2609.11929v1
        https://arxiv.org/pdf/2609.11929v1.pdf
    """

    paper_id = paper_id.strip()

    if "/abs/" in paper_id:
        paper_id = paper_id.split("/abs/")[-1]

    elif "/pdf/" in paper_id:
        paper_id = paper_id.split("/pdf/")[-1]
        paper_id = paper_id.removesuffix(".pdf")

    return paper_id.rstrip("/")


def extract_query_terms(query):
    """
    Extract meaningful terms for lexical search.

    Removes common question words while preserving
    meaningful research-related words.
    """

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


def build_query_variants(query):
    """
    Create a small set of generic query representations.

    The goal is not to hardcode paper sections or topics.
    Instead, we give both semantic and lexical retrieval
    slightly different views of the same user question.
    """

    original = query.strip()

    terms = extract_query_terms(original)

    variants = []

    # Original natural-language question.
    if original:
        variants.append(original)

    # Keyword-focused version.
    if terms:
        keyword_query = " ".join(terms)

        if keyword_query not in variants:
            variants.append(keyword_query)

    return variants


def vector_search(query, paper_id, top_k=VECTOR_TOP_K):
    """
    Semantic search using BGE embeddings.
    """

    paper_id = normalize_paper_id(paper_id)

    model = load_embedding_model()

    embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).tolist()

    response = supabase.rpc(
        "match_paper_chunks",
        {
            "query_embedding": embedding,
            "match_count": top_k,
            "target_paper_id": paper_id,
        },
    ).execute()

    return response.data or []


def lexical_search(query, paper_id, top_k=LEXICAL_TOP_K):
    """
    PostgreSQL full-text search.
    """

    paper_id = normalize_paper_id(paper_id)

    terms = extract_query_terms(query)

    if not terms:
        return []

    response = supabase.rpc(
        "search_paper_chunks_lexical",
        {
            "search_query": " ".join(terms),
            "match_count": top_k,
            "target_paper_id": paper_id,
        },
    ).execute()

    return response.data or []


def merge_candidates(vector_results, lexical_results):
    """
    Merge vector and lexical candidates by chunk ID.
    """

    candidates = {}

    for item in vector_results:
        candidates[item["id"]] = dict(item)

    for item in lexical_results:

        chunk_id = item["id"]

        if chunk_id in candidates:

            candidates[chunk_id]["lexical_score"] = item.get(
                "lexical_score",
                0,
            )

        else:
            candidates[chunk_id] = dict(item)

    return list(candidates.values())


def retrieve_candidates(query, paper_id):
    """
    Retrieve candidates using multiple generic representations
    of the same query.

    This improves robustness when natural-language wording varies.
    """

    all_candidates = {}

    query_variants = build_query_variants(query)

    for variant in query_variants:

        vector_results = vector_search(
            variant,
            paper_id,
            VECTOR_TOP_K,
        )

        lexical_results = lexical_search(
            variant,
            paper_id,
            LEXICAL_TOP_K,
        )

        candidates = merge_candidates(
            vector_results,
            lexical_results,
        )

        for item in candidates:

            chunk_id = item["id"]

            if chunk_id not in all_candidates:

                all_candidates[chunk_id] = dict(item)

            else:

                # Preserve the strongest lexical score when
                # the same chunk appears through multiple variants.
                old_score = all_candidates[chunk_id].get(
                    "lexical_score",
                    0,
                )

                new_score = item.get(
                    "lexical_score",
                    0,
                )

                all_candidates[chunk_id]["lexical_score"] = max(
                    old_score,
                    new_score,
                )

    return list(all_candidates.values())


def retrieve_best_chunks(
    query,
    paper_id,
    final_top_k=FINAL_TOP_K,
):
    """
    Full retrieval pipeline:

        query
          ↓
        query variants
          ↓
        vector + lexical retrieval
          ↓
        candidate merge
          ↓
        cross-encoder reranking
          ↓
        final chunks
    """

    paper_id = normalize_paper_id(paper_id)

    candidates = retrieve_candidates(
        query,
        paper_id,
    )

    if not candidates:
        return []

    return rerank_chunks(
        query,
        candidates,
        top_k=final_top_k,
    )


if __name__ == "__main__":

    paper_id = "2609.11916v1"

    questions = [
        "What is the main contribution?",
        "What are the main contributions of this paper?",
        "What is the paper about?",
        "What are the limitations?",
        "What are the limitations of this paper?",
    ]

    for q in questions:

        print("\n" + "=" * 80)
        print(q)
        print("=" * 80)

        print("\nQuery variants:")
        for variant in build_query_variants(q):
            print(f"  - {variant}")

        results = retrieve_best_chunks(
            q,
            paper_id,
            final_top_k=5,
        )

        if not results:
            print("\nNo relevant chunks found.")
            continue

        print("\nRetrieved chunks:")

        for i, chunk in enumerate(results, 1):

            score = chunk.get(
                "rerank_score",
                0,
            )

            print(
                f"{i}. "
                f"chunk={chunk['chunk_index']} "
                f"section={chunk.get('section')} "
                f"pages={chunk.get('page_start')}-"
                f"{chunk.get('page_end')} "
                f"score={score:.4f}"
            )