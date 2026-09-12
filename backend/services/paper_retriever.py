
import arxiv


# ------------------------------------------------------------
# arXiv configuration
# ------------------------------------------------------------

AI_CATEGORIES = {
    "cs.AI",
    "cs.LG",
    "cs.CV",
    "cs.CL",
    "cs.RO",
    "cs.NE",
    "cs.IR",
    "cs.MA",
    "stat.ML",
}


AI_TERMS = {
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "neural networks",
    "transformer",
    "transformers",
    "large language model",
    "large language models",
    "llm",
    "llms",
    "language model",
    "language models",
    "computer vision",
    "natural language processing",
    "nlp",
    "retrieval augmented generation",
    "retrieval-augmented generation",
    "rag",
    "agent",
    "agents",
    "multimodal",
    "reinforcement learning",
    "generative ai",
    "diffusion model",
    "diffusion models",
    "embedding",
    "embeddings",
    "foundation model",
    "foundation models",
}


# ------------------------------------------------------------
# arXiv client
# ------------------------------------------------------------

def create_arxiv_client():
    """
    Create a conservative arXiv client.

    The client uses:
    - a small page size
    - a delay between requests
    - retries for temporary failures
    """

    return arxiv.Client(
        page_size=20,
        delay_seconds=3,
        num_retries=3,
    )


# ------------------------------------------------------------
# AI relevance check
# ------------------------------------------------------------

def is_ai_relevant(paper):
    """
    Determine whether an arXiv paper is relevant to AI.

    Rule:
        Category = candidate signal
        Title + abstract = semantic evidence

    A paper must:
        1. Belong to at least one AI-related category.
        2. Contain at least one AI-related term in
           its title or abstract.
    """

    categories = set(
        getattr(paper, "categories", [])
    )

    # --------------------------------------------------------
    # Step 1: Category filter
    # --------------------------------------------------------

    if not categories.intersection(AI_CATEGORIES):
        return False

    # --------------------------------------------------------
    # Step 2: Title + abstract
    # --------------------------------------------------------

    title = (
        getattr(paper, "title", "")
        or ""
    ).lower()

    abstract = (
        getattr(paper, "summary", "")
        or ""
    ).lower()

    text = f"{title} {abstract}"

    # --------------------------------------------------------
    # Step 3: AI topic evidence
    # --------------------------------------------------------

    for term in AI_TERMS:
        if term in text:
            return True

    return False


# ------------------------------------------------------------
# Search recent AI papers
# ------------------------------------------------------------

def search_recent_ai_papers(
    max_results=20,
):
    """
    Retrieve the newest arXiv papers from AI-related categories.

    The search is performed using a single combined category
    query rather than making one request per category.

    This reduces the number of requests sent to arXiv.
    """

    category_query = " OR ".join(
        f"cat:{category}"
        for category in sorted(AI_CATEGORIES)
    )

    search = arxiv.Search(
        query=category_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    client = create_arxiv_client()

    results = []

    try:
        for paper in client.results(search):

            if is_ai_relevant(paper):
                results.append(paper)

            # ------------------------------------------------
            # We already requested max_results from arXiv.
            # No additional requests are made here.
            # ------------------------------------------------

            if len(results) >= max_results:
                break

    except Exception:
        # ----------------------------------------------------
        # Do NOT hide the exception from the detector.
        #
        # new_paper_detector.py will handle temporary
        # arXiv failures such as HTTP 429.
        # ----------------------------------------------------
        raise

    return results


# ------------------------------------------------------------
# Simple local test
# ------------------------------------------------------------

if __name__ == "__main__":

    print(
        "Searching arXiv for recent AI papers..."
    )

    papers = search_recent_ai_papers(
        max_results=20
    )

    print(
        f"\nFound {len(papers)} relevant papers.\n"
    )

    for index, paper in enumerate(
        papers,
        start=1,
    ):

        paper_id = (
            paper.entry_id
            .rstrip("/")
            .split("/")[-1]
        )

        print(
            f"{index}. {paper_id}"
        )

        print(
            f"   {paper.title}"
        )

        print(
            f"   Categories: "
            f"{', '.join(paper.categories)}"
        )

        print()

