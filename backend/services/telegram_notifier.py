
import html
import re
import requests

from backend.database.supabase_database import supabase
from backend.services.config import TELEGRAM_BOT_TOKEN


TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
)


# ---------------------------------------------------------
# SEND MESSAGE
# ---------------------------------------------------------

def send_message(
    chat_id,
    text,
    reply_markup=None,
    parse_mode="HTML",
):
    """
    Send a message to a Telegram chat.
    """

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    response = requests.post(
        f"{TELEGRAM_API_URL}/sendMessage",
        json=payload,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {data}"
        )

    return data


# ---------------------------------------------------------
# REGISTER TELEGRAM SUBSCRIBER
# ---------------------------------------------------------

def register_subscriber(
    chat_id,
    username=None,
    first_name=None,
):
    """
    Register or reactivate a Telegram subscriber.
    """

    row = {
        "chat_id": str(chat_id),
        "username": username,
        "active": True,
    }

    supabase.table(
        "telegram_subscribers"
    ).upsert(
        row,
        on_conflict="chat_id",
    ).execute()


# ---------------------------------------------------------
# GET ACTIVE SUBSCRIBERS
# ---------------------------------------------------------

def get_active_subscribers():
    """
    Return all active Telegram chat IDs.
    """

    response = (
        supabase
        .table("telegram_subscribers")
        .select("chat_id")
        .eq("active", True)
        .execute()
    )

    return [
        row["chat_id"]
        for row in response.data
    ]


# ---------------------------------------------------------
# CREATE MINIMAL PAPER SUMMARY
# ---------------------------------------------------------

def create_short_summary(abstract):
    """
    Create a very short notification summary.

    Strategy:
    1. Normalize whitespace.
    2. Use the first complete sentence if it is short enough.
    3. If it is too long, keep the beginning as a
       short teaser.

    No LLM call is made here so that notifications
    remain fast.
    """

    if not abstract:
        return "No summary available."

    # Remove unnecessary whitespace/newlines.
    text = " ".join(abstract.split()).strip()

    if not text:
        return "No summary available."

    # Split into sentences.
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    first_sentence = sentences[0].strip()

    # Keep a complete first sentence when reasonably short.
    if len(first_sentence) <= 180:
        return first_sentence

    # Otherwise create a short teaser.
    words = first_sentence.split()

    summary = ""

    for word in words:
        candidate = (
            f"{summary} {word}"
            if summary
            else word
        )

        if len(candidate) > 150:
            break

        summary = candidate

    summary = summary.rstrip(
        " ,;:"
    )

    if summary:
        return summary + "..."

    return "No summary available."


# ---------------------------------------------------------
# FORMAT AUTHORS
# ---------------------------------------------------------

def format_authors(authors):
    """
    Show a maximum of three authors.

    Examples:

    1 author:
        John Smith

    2 authors:
        John Smith, Jane Doe

    3 authors:
        John Smith, Jane Doe, Alex Kumar

    More than 3:
        John Smith, Jane Doe, Alex Kumar et al.
    """

    if not authors:
        return "Unknown authors"

    # Support both a list and a string.
    if isinstance(authors, str):
        author_list = [
            author.strip()
            for author in authors.split(",")
            if author.strip()
        ]
    else:
        author_list = [
            str(author).strip()
            for author in authors
            if str(author).strip()
        ]

    if not author_list:
        return "Unknown authors"

    if len(author_list) <= 3:
        return ", ".join(author_list)

    return (
        ", ".join(author_list[:3])
        + " et al."
    )


# ---------------------------------------------------------
# EXTRACT PAPER ID
# ---------------------------------------------------------

def extract_paper_id(paper):
    """
    Extract the arXiv paper ID from an arXiv entry.
    """

    entry_id = getattr(
        paper,
        "entry_id",
        None,
    )

    if entry_id:
        return (
            entry_id
            .rstrip("/")
            .split("/")
            [-1]
        )

    paper_id = getattr(
        paper,
        "paper_id",
        None,
    )

    if paper_id:
        return str(paper_id)

    raise ValueError(
        "Could not determine paper ID."
    )


# ---------------------------------------------------------
# EXTRACT PAPER DATA
# ---------------------------------------------------------

def get_paper_data(paper):
    """
    Convert an arXiv paper object or dictionary
    into the fields required for notification.
    """

    if isinstance(paper, dict):

        title = paper.get(
            "title",
            "Untitled Paper",
        )

        abstract = paper.get(
            "abstract",
            "",
        )

        authors = paper.get(
            "authors",
            [],
        )

        paper_id = paper.get(
            "paper_id",
        )

        arxiv_url = paper.get(
            "arxiv_url",
        )

    else:

        title = getattr(
            paper,
            "title",
            "Untitled Paper",
        )

        abstract = getattr(
            paper,
            "summary",
            "",
        )

        author_objects = getattr(
            paper,
            "authors",
            [],
        )

        authors = [
            getattr(
                author,
                "name",
                str(author),
            )
            for author in author_objects
        ]

        paper_id = extract_paper_id(
            paper
        )

        arxiv_url = getattr(
            paper,
            "entry_id",
            None,
        )

    if not paper_id:
        raise ValueError(
            "Paper ID is missing."
        )

    if not arxiv_url:
        arxiv_url = (
            f"https://arxiv.org/abs/"
            f"{paper_id}"
        )

    return {
        "title": str(title).strip(),
        "abstract": str(abstract).strip(),
        "authors": authors,
        "paper_id": str(paper_id).strip(),
        "arxiv_url": arxiv_url,
    }


# ---------------------------------------------------------
# CREATE INLINE KEYBOARD
# ---------------------------------------------------------

def create_paper_keyboard(paper_id):
    """
    Create the inline Telegram button used
    to select the paper for questioning.
    """

    return {
        "inline_keyboard": [
            [
                {
                    "text": "📖 Ask about this paper",
                    "callback_data": (
                        f"paper:{paper_id}"
                    ),
                }
            ]
        ]
    }


# ---------------------------------------------------------
# CREATE NOTIFICATION MESSAGE
# ---------------------------------------------------------

def create_notification_message(paper):
    """
    Build the complete Telegram notification.
    """

    data = get_paper_data(paper)

    title = html.escape(
        data["title"]
    )

    authors = html.escape(
        format_authors(
            data["authors"]
        )
    )

    summary = html.escape(
        create_short_summary(
            data["abstract"]
        )
    )

    paper_id = html.escape(
        data["paper_id"]
    )

    arxiv_url = html.escape(
        data["arxiv_url"],
        quote=True,
    )

    message = (
        "🆕 <b>New AI Research Paper</b>\n\n"
        f"📄 <b>{title}</b>\n\n"
        f"👥 <b>Authors:</b>\n"
        f"{authors}\n\n"
        f"📝 <b>Summary:</b>\n"
        f"{summary}\n\n"
        f'🔗 <a href="{arxiv_url}">'
        f"arXiv: {paper_id}"
        f"</a>"
    )

    keyboard = create_paper_keyboard(
        data["paper_id"]
    )

    return message, keyboard


# ---------------------------------------------------------
# NOTIFY ALL SUBSCRIBERS
# ---------------------------------------------------------

def notify_new_paper(paper):
    """
    Send a new-paper notification to
    every active Telegram subscriber.
    """

    message, keyboard = (
        create_notification_message(
            paper
        )
    )

    subscribers = get_active_subscribers()

    if not subscribers:
        print(
            "No active Telegram subscribers."
        )
        return

    success_count = 0
    failure_count = 0

    for chat_id in subscribers:

        try:

            send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            success_count += 1

            print(
                f"Notification sent to {chat_id}"
            )

        except Exception as e:

            failure_count += 1

            print(
                f"Failed to notify {chat_id}: {e}"
            )

    print(
        f"Telegram notification complete. "
        f"Success: {success_count}, "
        f"Failed: {failure_count}"
    )


# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    print(
        "telegram_notifier.py loaded successfully."
    )

    subscribers = get_active_subscribers()

    print(
        f"Active subscribers: {len(subscribers)}"
    )

