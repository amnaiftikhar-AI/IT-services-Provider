from langchain_text_splitters import RecursiveCharacterTextSplitter

SEPARATORS = [
    "\n# ",
    "\n## ",
    "\n### ",
    "\nSection ",
    "\nARTICLE ",
    "\nClause ",
    "\n\n",
    "\n",
    ". ",
    " ",
    "",
]


def split_document(text: str, chunk_size: int = 2000, chunk_overlap: int = 300) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        length_function=len,
        keep_separator=True,
    )
    return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
