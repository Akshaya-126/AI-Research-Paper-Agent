from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader

@dataclass
class PageText:
    page_number: int
    text: str

def extract_pages(pdf_path: Path):
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(PageText(i, text))
    return pages
