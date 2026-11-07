
from pathlib import Path
from hashlib import sha256

from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from amna_rag.models import KBDocument, KBSection, KBChunk
from amna_rag.config import settings
from amna_rag.services.document_loader import (
    load_uploaded_file,
    attach_section_headings,
)
from amna_rag.services.index_service import add_documents, rebuild_index


SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=850,
    chunk_overlap=140,
    separators=["\n## ", "\n# ", "\n\n", "\n", ". ", " ", ""],
    add_start_index=True,
)


def ingest_file(
    db: Session,
    filename: str,
    content: bytes,
    uploaded_by: str,
    document_type: str = "Technical Guide",
    department: str = "IT",
    system_name: str = "General IT",
):
    digest = sha256(content).hexdigest()

    # 1. Check whether this file already exists
    existing = (
        db.query(KBDocument)
        .filter_by(content_hash=digest)
        .first()
    )

    if existing:
        raise ValueError(
            f"This file is already uploaded as {existing.filename}"
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{digest[:12]}_{Path(filename).name}"
    file_path = upload_dir / safe_name

    try:
        # 2. Save the uploaded file
        file_path.write_bytes(content)

        # 3. Create document database record
        doc = KBDocument(
            filename=Path(filename).name,
            file_type=Path(filename).suffix.lower().lstrip("."),
            document_type=document_type,
            department=department,
            system_name=system_name,
            file_path=str(file_path),
            content_hash=digest,
            uploaded_by=uploaded_by,
        )

        db.add(doc)
        db.flush()

        # 4. Load document content and attach section headings
        page_blocks = attach_section_headings(
            load_uploaded_file(filename, content)
        )

        # 5. Group content by page and section
        grouped_sections = {}

        for block in page_blocks:
            key = (
                block.metadata.get("page"),
                block.metadata.get("section", "General"),
            )

            grouped_sections.setdefault(key, []).append(
                block.page_content
            )

        chunks = []

        # 6. Create parent sections and searchable child chunks
        for (page_number, section_title), section_blocks in grouped_sections.items():

            section_text = "\n\n".join(section_blocks)

            parent = KBSection(
                document_id=doc.id,
                section_title=section_title,
                page_number=page_number,
                content=section_text,
            )

            db.add(parent)
            db.flush()

            parent_doc = Document(
                page_content=section_text,
                metadata={
                    "page": page_number,
                    "section": section_title,
                },
            )

            split_docs = SPLITTER.split_documents([parent_doc])

            for split_doc in split_docs:
                if not split_doc.page_content.strip():
                    continue

                # 7. Create consistent metadata for every chunk
                meta = {
                    **split_doc.metadata,
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "source": doc.filename,
                    "document_type": document_type,
                    "department": department,
                    "system_name": system_name,
                    "page": page_number,
                    "section": section_title,
                    "parent_section_id": parent.id,
                }

                chunk = KBChunk(
                    document_id=doc.id,
                    parent_section_id=parent.id,
                    chunk_index=len(chunks),
                    content=split_doc.page_content,
                    parent_section=section_title,
                    page_number=page_number,
                    metadata_json=meta,
                )

                db.add(chunk)
                db.flush()

                # Add database chunk ID to metadata
                meta["chunk_id"] = chunk.id

                # Keep chunk and its metadata together
                chunks.append((chunk, meta))

        # 8. Save document, sections and chunks
        db.commit()

        # 9. Add chunks to FAISS
        documents = [
            Document(
                page_content=chunk.content,
                metadata=metadata,
            )
            for chunk, metadata in chunks
        ]

        add_documents(documents)

        # 10. Mark document as indexed
        doc.is_indexed = True
        db.commit()

        return doc, len(chunks)

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise


def rebuild_all(db: Session):
    # 1. Retrieve all chunks with their parent documents
    rows = (
        db.query(KBChunk, KBDocument)
        .join(KBDocument, KBChunk.document_id == KBDocument.id)
        .all()
    )

    items = []

    # 2. Reconstruct consistent metadata
    for chunk, doc in rows:

        metadata = {
            **(chunk.metadata_json or {}),
            "chunk_id": chunk.id,
            "document_id": doc.id,
            "filename": doc.filename,
            "source": doc.filename,
            "page": chunk.page_number,
            "section": chunk.parent_section,
            "document_type": doc.document_type,
            "department": doc.department,
            "system_name": doc.system_name,
        }

        items.append({
            "content": chunk.content,
            "metadata": metadata,
        })

    # 3. Rebuild FAISS index
    count = rebuild_index(items)

    # 4. Update indexing status
    for doc in db.query(KBDocument).all():
        doc.is_indexed = True

    db.commit()

    return count


def delete_document(db: Session, document: KBDocument):
    # 1. Remove document file
    path = Path(document.file_path)

    # 2. Delete database record and associated records
    db.delete(document)
    db.commit()

    path.unlink(missing_ok=True)

    # 3. Rebuild index without deleted document
    rebuild_all(db)
