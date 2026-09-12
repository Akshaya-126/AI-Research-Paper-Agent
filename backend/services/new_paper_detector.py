from backend.services.paper_retriever import search_recent_ai_papers
from backend.services.ai_relevance_agent import classify_paper
from backend.services.paper_pipeline import ingest_paper
from backend.services.vector_database import paper_exists
from backend.services.telegram_notifier import notify_new_paper


# ------------------------------------------------------------
# arXiv retry configuration
# ------------------------------------------------------------

INITIAL_RETRY_DELAY = 60
MAX_RETRY_DELAY = 900


def is_rate_limit_error(exc):
    """
    Check whether an exception is caused by arXiv HTTP 429.
    """
    error_text = str(exc).lower()

    return (
        "429" in error_text
        or "too many requests" in error_text
        or "rate limit" in error_text
    )


def search_arxiv_with_retry():
    """
    Search arXiv once.

    If arXiv temporarily fails or rate-limits the request,
    retry using exponential backoff.
    """

    retry_delay = INITIAL_RETRY_DELAY

    while True:

        try:
            papers = search_recent_ai_papers()

            print(
                f"Checked arXiv. "
                f"Found {len(papers)} relevant AI papers."
            )

            return papers

        except Exception as exc:

            if is_rate_limit_error(exc):

                print(
                    "\n"
                    "arXiv rate limit reached (HTTP 429).\n"
                    f"Waiting {retry_delay} seconds "
                    "before retrying.\n"
                )

                import time
                time.sleep(retry_delay)

                retry_delay = min(
                    retry_delay * 2,
                    MAX_RETRY_DELAY,
                )

            else:

                print(
                    "\n"
                    f"arXiv request failed: {exc}"
                )

                print(
                    f"Retrying in {retry_delay} seconds...\n"
                )

                import time
                time.sleep(retry_delay)

                retry_delay = min(
                    retry_delay * 2,
                    MAX_RETRY_DELAY,
                )


def run_daily_check():
    """
    Run one complete daily arXiv processing cycle.

    Flow:

        arXiv
          ↓
        AI relevance filter
          ↓
        Check processed status
          ↓
        PDF ingestion
          ↓
        Chunks + embeddings
          ↓
        Supabase
          ↓
        Telegram notification
          ↓
        Exit
    """

    print("=" * 60)
    print("AI Research Paper Agent - Daily Check")
    print("=" * 60)

    # ========================================================
    # STEP 1: SEARCH ARXIV
    # ========================================================

    papers = search_arxiv_with_retry()

    if not papers:

        print("No relevant AI papers found.")
        print("Daily check completed.")
        return

    # ========================================================
    # STEP 2: PROCESS PAPERS
    # ========================================================

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    # Process oldest first.
    for paper in reversed(papers):

        # ----------------------------------------------------
        # STEP 2A: AI relevance filtering
        # ----------------------------------------------------

        try:

            if not classify_paper(paper):

                print(
                    f"Skipped non-AI paper: "
                    f"{paper.title}"
                )

                skipped_count += 1
                continue

        except Exception as exc:

            print(
                "AI relevance classification failed "
                f"for {paper.title}: {exc}"
            )

            failed_count += 1
            continue

        # ----------------------------------------------------
        # STEP 2B: Get arXiv paper ID
        # ----------------------------------------------------

        paper_id = (
            paper.entry_id
            .rstrip("/")
            .split("/")[-1]
        )

        # ----------------------------------------------------
        # STEP 2C: Check whether already processed
        #
        # paper_exists() checks paper_chunks.
        #
        # chunks exist
        #     → already processed
        #
        # no chunks
        #     → process the paper
        # ----------------------------------------------------

        try:

            if paper_exists(paper_id):

                print(
                    f"Already processed: "
                    f"{paper_id}"
                )

                skipped_count += 1
                continue

        except Exception as exc:

            print(
                f"Database check failed for "
                f"{paper_id}: {exc}"
            )

            failed_count += 1
            continue

        # ----------------------------------------------------
        # STEP 2D: INGEST PAPER
        # ----------------------------------------------------

        try:

            chunk_count = ingest_paper(paper)

            if not chunk_count:

                print(
                    f"No chunks stored for "
                    f"{paper_id}."
                )

                print(
                    "Telegram notification skipped."
                )

                failed_count += 1
                continue

            print("\n" + "-" * 60)
            print(
                f"New paper ingested: "
                f"{paper.title}"
            )
            print(
                f"Paper ID: {paper_id}"
            )
            print(
                f"Chunks stored: {chunk_count}"
            )
            print("-" * 60)

            # ------------------------------------------------
            # STEP 2E: TELEGRAM NOTIFICATION
            # ------------------------------------------------

            try:

                notify_new_paper(paper)

                print(
                    f"Telegram notification sent "
                    f"for {paper_id}"
                )

            except Exception as exc:

                print(
                    "Telegram notification failed "
                    f"for {paper_id}: {exc}"
                )

            processed_count += 1

        except Exception as exc:

            print(
                f"Ingestion failed for "
                f"{paper_id}: {exc}"
            )

            failed_count += 1
            continue

    # ========================================================
    # DAILY SUMMARY
    # ========================================================

    print("\n" + "=" * 60)
    print("Daily check completed.")
    print(f"Processed : {processed_count}")
    print(f"Skipped   : {skipped_count}")
    print(f"Failed    : {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    run_daily_check()