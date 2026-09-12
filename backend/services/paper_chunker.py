
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_index: int
    section: str
    subsection: str | None
    page_start: int
    page_end: int
    chunk_text: str


HEADING_RE = re.compile(
    r"^\s*((?:\d+(?:\.\d+)*)?[\s.)-]*"
    r"(?:abstract|introduction|background|related work|"
    r"method(?:ology)?|methods|experiments?|evaluation|"
    r"results?|discussion|limitations?|conclusion|references)"
    r")\s*$",
    re.I,
)


def clean(text: str) -> str:
    """
    Clean extracted PDF text before creating chunks.

    Removes:
    - NULL characters that PostgreSQL text cannot store
    - hyphenation caused by PDF line breaks
    - excessive newlines
    - excessive spaces/tabs
    """

    # IMPORTANT:
    # PostgreSQL rejects the Unicode NULL character (\x00).
    text = text.replace("\x00", "")

    # Remove other problematic control characters while preserving
    # normal newlines and tabs.
    text = "".join(
        char
        for char in text
        if char in "\n\t" or not ord(char) < 32
    )

    # Join words split across PDF line breaks.
    text = re.sub(r"-\n(?=\w)", "", text)

    # Collapse multiple newlines.
    text = re.sub(r"\n+", "\n", text)

    # Collapse spaces and tabs.
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def chunk_pages(pages, max_chars=2200, overlap=350):
    chunks = []

    current = []
    current_chars = 0

    section = "Document"
    subsection = None

    start_page = 1
    index = 0
    current_page = 1

    def flush():
        nonlocal current
        nonlocal current_chars
        nonlocal start_page
        nonlocal index

        if not current:
            return

        text = clean("\n".join(current))

        if text:
            chunks.append(
                Chunk(
                    chunk_index=index,
                    section=section,
                    subsection=subsection,
                    page_start=start_page,
                    page_end=current_page,
                    chunk_text=text,
                )
            )

            index += 1

        current = []
        current_chars = 0

    for page in pages:

        current_page = page.page_number

        for raw_line in page.text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            # Detect section headings.
            match = HEADING_RE.match(line)

            if match:
                flush()

                section = match.group(1).strip()
                subsection = None
                start_page = page.page_number

                continue

            # Start a new chunk when the maximum size is reached.
            if current_chars + len(line) + 1 > max_chars:

                old = "\n".join(current)

                flush()

                # Keep the last part of the previous chunk as overlap.
                overlap_text = old[-overlap:] if overlap else ""

                if overlap_text:
                    overlap_text = clean(overlap_text)

                    if overlap_text:
                        current = [overlap_text]
                        current_chars = len(overlap_text)
                        start_page = page.page_number

            current.append(line)
            current_chars += len(line) + 1

    # Flush the final chunk.
    flush()

    return chunks

