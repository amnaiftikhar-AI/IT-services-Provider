from pathlib import Path
from tempfile import NamedTemporaryFile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
import re

HEADING_RE = re.compile(r"^(?:#{1,6}\s+|[A-Z][A-Z0-9 /&()_-]{3,}:?$)")

def load_uploaded_file(filename: str, file_bytes: bytes) -> list[Document]:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise ValueError("Only PDF and TXT files are supported")
    with NamedTemporaryFile(suffix=suffix, delete=False) as temp:
        temp.write(file_bytes)
        temp_path = temp.name
    try:
        if suffix == ".pdf":
            pages = PyPDFLoader(temp_path).load()
        else:
            pages = TextLoader(temp_path, encoding="utf-8").load()
        for page in pages:
            page.metadata["source"] = filename
            page.metadata["page"] = int(page.metadata.get("page", 0)) + (1 if suffix == ".pdf" else 0)
        return pages
    finally:
        Path(temp_path).unlink(missing_ok=True)

def attach_section_headings(pages: list[Document]) -> list[Document]:
    """Keep a section label on each block before recursive splitting."""
    result = []
    current_heading = "General"
    for page in pages:
        blocks = re.split(r"\n(?=\S)", page.page_content)
        for block in blocks:
            line = block.strip()
            if not line:
                continue
            first_line = line.splitlines()[0].strip()
            if HEADING_RE.match(first_line):
                current_heading = first_line.lstrip("# ").rstrip(":")[:250]
            result.append(Document(page_content=line, metadata={**page.metadata, "section": current_heading}))
    return result
