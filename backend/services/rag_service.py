from backend.database.supabase_database import supabase

from backend.services.vector_search import (
    retrieve_best_chunks,
    normalize_paper_id,
)

from backend.services.llm_service import generate_answer


# ============================================================
# RAG SETTINGS
# ============================================================

# Number of best chunks sent to the LLM.
#
# Retrieval and reranking remain unchanged.
RAG_TOP_K = 3

# Maximum number of characters from each retrieved chunk
# that will be included in the LLM context.
MAX_CHUNK_CHARS = 1800


# ============================================================
# PAPER METADATA
# ============================================================

def get_paper(paper_id):
    """
    Retrieve paper metadata from Supabase.
    """

    paper_id = normalize_paper_id(paper_id)

    response = (
        supabase.table("papers")
        .select(
            "title,abstract,authors,arxiv_url"
        )
        .eq(
            "paper_id",
            paper_id
        )
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None


# ============================================================
# BUILD COMPACT RAG CONTEXT
# ============================================================

def build_context(chunks):
    """
    Build a compact context for the LLM.

    The chunks have already been selected by:

        1. Vector search
        2. Lexical search
        3. Cross-encoder reranking

    Only the highest-ranked chunks should reach the LLM.

    Each chunk is capped at MAX_CHUNK_CHARS so that
    unnecessarily large PDF chunks do not create excessive
    context.
    """

    blocks = []

    for i, chunk in enumerate(chunks, 1):

        # ----------------------------------------------------
        # Section information
        # ----------------------------------------------------

        source = (
            f"Section: "
            f"{chunk.get('section') or 'Unknown'}"
        )

        if chunk.get("subsection"):

            source += (
                f" | Subsection: "
                f"{chunk['subsection']}"
            )

        source += (
            f" | Pages: "
            f"{chunk.get('page_start')}"
            f"–"
            f"{chunk.get('page_end')}"
        )

        # ----------------------------------------------------
        # Chunk text
        # ----------------------------------------------------

        text = chunk.get(
            "chunk_text",
            ""
        ).strip()

        # ----------------------------------------------------
        # Limit context size
        # ----------------------------------------------------

        if len(text) > MAX_CHUNK_CHARS:

            shortened = text[:MAX_CHUNK_CHARS]

            # Try to avoid cutting a word in half.
            last_space = shortened.rfind(" ")

            if last_space > 0:
                shortened = shortened[:last_space]

            text = shortened + "..."

        # ----------------------------------------------------
        # Create source block
        # ----------------------------------------------------

        blocks.append(
            f"[SOURCE {i}]\n"
            f"{source}\n"
            f"{text}"
        )

    return "\n\n".join(blocks)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_llm(question, context, paper):
    """
    Ask Gemini to answer strictly from the supplied
    paper metadata and retrieved paper context.

    Gemini does NOT generate the final Sources section.
    Python generates that separately.
    """

    # ========================================================
    # SYSTEM INSTRUCTION
    # ========================================================

    system = """
You are ResearchX AI, a research-paper question answering assistant.

Your job is to answer the user's question using ONLY the
supplied paper information and retrieved paper context.

STRICT RULES:

1. Use only information contained in the supplied paper
   information and retrieved paper context.

2. Do not use outside knowledge.

3. Do not make assumptions that are not supported by
   the supplied context.

4. Do not invent experiments, datasets, results, numbers,
   authors, methods, conclusions, or limitations.

5. If the retrieved context does not contain enough
   information to answer the question, clearly say:

   "The available paper context does not contain enough
   information to answer this."

6. You may refer to retrieved evidence using [SOURCE N].

7. Do NOT create a Sources section.

8. Do NOT create page numbers yourself.

9. Do NOT create source numbers that do not exist.

10. Keep the answer concise and directly answer the
    user's question.

11. Do not mention information that is not supported by
    the supplied paper context.

12. If the question asks about something unrelated to
    the selected paper and the retrieved context does not
    contain the answer, use the exact insufficient-context
    response from rule 5.

13. Treat the retrieved context as the only evidence source
    for factual claims about the paper.

The SOURCE numbers correspond exactly to the retrieved
chunks provided below.
"""

    # ========================================================
    # USER PROMPT
    # ========================================================

    prompt = f"""
PAPER TITLE:
{paper.get('title', '')}

PAPER AUTHORS:
{paper.get('authors', '')}

PAPER ABSTRACT:
{paper.get('abstract', '')}

RETRIEVED PAPER CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    # ========================================================
    # GEMINI REQUEST
    # ========================================================

    return generate_answer(
        system_instruction=system,
        prompt=prompt,
    )


# ============================================================
# BUILD SOURCES
# ============================================================

def build_sources(chunks):
    """
    Generate the final source list from the chunks actually
    retrieved.

    This is intentionally done by Python rather than Gemini
    so that source information cannot be hallucinated.
    """

    sources = []

    seen = set()

    for chunk in chunks:

        section = (
            chunk.get("section")
            or "Unknown"
        )

        subsection = chunk.get(
            "subsection"
        )

        page_start = chunk.get(
            "page_start"
        )

        page_end = chunk.get(
            "page_end"
        )

        # ----------------------------------------------------
        # Unique source identifier
        # ----------------------------------------------------

        source_key = (
            section,
            subsection,
            page_start,
            page_end,
        )

        # ----------------------------------------------------
        # Avoid duplicate sources
        # ----------------------------------------------------

        if source_key in seen:
            continue

        seen.add(source_key)

        sources.append(
            {
                "section": section,
                "subsection": subsection,
                "page_start": page_start,
                "page_end": page_end,
            }
        )

    return sources


# ============================================================
# FORMAT SOURCES FOR TELEGRAM
# ============================================================

def format_sources(sources):
    """
    Convert structured source information into a
    Telegram-friendly Sources section.
    """

    if not sources:
        return ""

    lines = [
        "Sources:"
    ]

    for source in sources:

        section = source["section"]

        # ----------------------------------------------------
        # Add subsection if available
        # ----------------------------------------------------

        if source.get("subsection"):

            section += (
                f" → "
                f"{source['subsection']}"
            )

        # ----------------------------------------------------
        # Page information
        # ----------------------------------------------------

        page_start = source.get(
            "page_start"
        )

        page_end = source.get(
            "page_end"
        )

        if page_start and page_end:

            if page_start == page_end:

                pages = (
                    f"p. {page_start}"
                )

            else:

                pages = (
                    f"pp. "
                    f"{page_start}–"
                    f"{page_end}"
                )

            lines.append(
                f"• {section} ({pages})"
            )

        elif page_start:

            lines.append(
                f"• {section} "
                f"(p. {page_start})"
            )

        else:

            lines.append(
                f"• {section}"
            )

    return "\n".join(lines)


# ============================================================
# COMPLETE RAG PIPELINE
# ============================================================

def answer_question(
    question,
    paper_id,
    top_k=RAG_TOP_K,
):
    """
    Complete RAG question-answering pipeline.

    Flow:

        Question
            ↓
        Vector Search
            +
        Lexical Search
            ↓
        Candidate Merge
            ↓
        Cross-Encoder Reranking
            ↓
        Top 3 chunks
            ↓
        Context Size Control
            ↓
        Gemini
            ↓
        Answer
            ↓
        Python-generated Sources
    """

    # ========================================================
    # 1. RETRIEVE BEST CHUNKS
    # ========================================================

    chunks = retrieve_best_chunks(
        question,
        paper_id,
        top_k,
    )

    if not chunks:

        return {
            "answer": (
                "I could not retrieve relevant "
                "context from this paper."
            ),
            "sources": [],
            "chunks": [],
        }

    # ========================================================
    # 2. GET PAPER METADATA
    # ========================================================

    paper = get_paper(
        paper_id
    )

    if not paper:

        raise ValueError(
            "Paper metadata was not found "
            "in Supabase."
        )

    # ========================================================
    # 3. BUILD COMPACT CONTEXT
    # ========================================================

    context = build_context(
        chunks
    )

    # ========================================================
    # 4. ASK GEMINI
    # ========================================================

    answer = ask_llm(
        question,
        context,
        paper,
    )

    # ========================================================
    # 5. GENERATE SOURCES USING PYTHON
    # ========================================================

    sources = build_sources(
        chunks
    )

    source_text = format_sources(
        sources
    )

    # ========================================================
    # 6. FINAL ANSWER
    # ========================================================

    if source_text:

        final_answer = (
            f"{answer}\n\n"
            f"{source_text}"
        )

    else:

        final_answer = answer

    # ========================================================
    # 7. RETURN RESULT
    # ========================================================

    return {
        "answer": final_answer,
        "sources": sources,
        "chunks": chunks,
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    result = answer_question(
        "What experiments were performed?",
        "2609.11929v1",
    )

    print()
    print("=" * 80)
    print("RAG ANSWER")
    print("=" * 80)
    print()

    print(
        result["answer"]
    )

    print()
    print("=" * 80)
    print("RETRIEVED CHUNKS")
    print("=" * 80)

    for i, chunk in enumerate(
        result["chunks"],
        1,
    ):

        print()
        print(
            f"Chunk {i}"
        )

        print(
            f"Section: "
            f"{chunk.get('section')}"
        )

        print(
            f"Pages: "
            f"{chunk.get('page_start')}"
            f"–"
            f"{chunk.get('page_end')}"
        )

        print(
            f"Rerank score: "
            f"{chunk.get('rerank_score')}"
        )