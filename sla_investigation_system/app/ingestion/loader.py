import fitz
from pathlib import Path

def load_file(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        pages = []
        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                pages.append({"text": page.get_text(), "page_number": page_number})
        return pages
    if path.suffix.lower() == ".txt":
        return [{"text": path.read_text(encoding="utf-8"), "page_number": None}]
    raise ValueError("Only PDF and TXT files are supported.")
