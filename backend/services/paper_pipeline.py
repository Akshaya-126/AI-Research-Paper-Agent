from backend.services.pdf_downloader import download_pdf
from backend.services.pdf_text_extractor import extract_pages
from backend.services.paper_chunker import chunk_pages
from backend.services.embedding_service import generate_embeddings
from backend.services.vector_database import (
    upsert_paper,
    store_chunks,
    get_paper_id,
)
from backend.services.config import PAPERS_DIR


def ingest_paper(paper):
    print(f"\nIngesting: {paper.title}")

    # Use exactly the same paper_id everywhere.
    paper_id = get_paper_id(paper)

    # Store paper metadata first.
    upsert_paper(paper)

    pdf_url = (
        paper.pdf_url
        if getattr(paper, "pdf_url", None)
        else f"https://arxiv.org/pdf/{paper_id}.pdf"
    )

    pdf_path = PAPERS_DIR / f"{paper_id}.pdf"

    # Download PDF.
    download_pdf(pdf_url, pdf_path)

    # Extract pages.
    pages = extract_pages(pdf_path)

    # Create section-aware chunks.
    chunks = chunk_pages(pages)

    print(f"Pages: {len(pages)}")
    print(f"Chunks: {len(chunks)}")

    # Generate BGE embeddings.
    texts = [c.chunk_text for c in chunks]
    embeddings = generate_embeddings(texts)

    # Store chunks using the SAME paper_id as papers.paper_id.
    count = store_chunks(
        paper_id,
        chunks,
        embeddings,
    )

    print(f"Stored chunks: {count}")

    return count


if __name__ == "__main__":
    from backend.services.paper_retriever import search_recent_ai_papers

    papers = search_recent_ai_papers(1)

    if not papers:
        raise SystemExit("No relevant paper found.")

    ingest_paper(papers[0])