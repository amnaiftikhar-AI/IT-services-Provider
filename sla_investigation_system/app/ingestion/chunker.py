from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

def split_pages(pages, chunk_size=700, chunk_overlap=120):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for page in pages:
        text = page["text"]
        heading = ""
        for line in text.splitlines():
            clean = line.strip()
            if clean and (clean.isupper() or re.match(r"^(section|chapter|policy)\s", clean, re.I)):
                heading = clean[:300]
        for index, part in enumerate(splitter.split_text(text)):
            if part.strip():
                chunks.append({
                    "content": part.strip(),
                    "section": heading or "General",
                    "page_number": page.get("page_number"),
                    "chunk_index": index
                })
    return chunks
