
from backend.database.supabase_database import supabase


def get_paper_id(paper):
    """
    Extract the arXiv paper ID from the paper entry URL.

    Example:
        https://arxiv.org/abs/2609.11916v1
        -> 2609.11916v1
    """
    return paper.entry_id.rstrip("/").split("/")[-1]


def upsert_paper(paper):
    """
    Insert or update paper metadata in the papers table.
    """

    paper_id = get_paper_id(paper)

    row = {
        "paper_id": paper_id,
        "title": paper.title,
        "abstract": paper.summary,
        "authors": ", ".join(
            author.name for author in paper.authors
        ),
        "published_at": (
            paper.published.isoformat()
            if paper.published
            else None
        ),
        "arxiv_url": paper.entry_id,
        "pdf_url": (
            paper.pdf_url
            if getattr(paper, "pdf_url", None)
            else paper.entry_id.replace(
                "/abs/",
                "/pdf/"
            ) + ".pdf"
        ),
        "category": ", ".join(
            paper.categories
        ),
    }

    supabase.table("papers").upsert(
        row,
        on_conflict="paper_id"
    ).execute()


def paper_exists(paper_id):
    """
    Check whether the paper has actually been processed.

    A paper is considered processed only when
    at least one chunk exists in paper_chunks.

    This prevents papers with metadata but zero chunks
    from being incorrectly skipped by the detector.
    """

    paper_id = paper_id.strip()

    response = (
        supabase.table("paper_chunks")
        .select("id")
        .eq("paper_id", paper_id)
        .limit(1)
        .execute()
    )

    return bool(response.data)


def store_chunks(paper_id, chunks, embeddings):
    """
    Store paper chunks and their embeddings in Supabase.
    """

    # Delete existing chunks before reprocessing.
    supabase.table("paper_chunks").delete().eq(
        "paper_id",
        paper_id
    ).execute()

    rows = []

    for chunk, embedding in zip(chunks, embeddings):

        # Convert NumPy array to Python list.
        vector = (
            embedding.tolist()
            if hasattr(embedding, "tolist")
            else list(embedding)
        )

        # BGE-small-en-v1.5 produces 384-dimensional embeddings.
        if len(vector) != 384:
            raise ValueError(
                f"Expected 384 dimensions, got {len(vector)}"
            )

        rows.append({
            "paper_id": paper_id,
            "chunk_index": chunk.chunk_index,
            "section": chunk.section,
            "subsection": chunk.subsection,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "chunk_text": chunk.chunk_text,
            "embedding": vector,
        })

    if rows:
        supabase.table("paper_chunks").insert(
            rows
        ).execute()

    return len(rows)

