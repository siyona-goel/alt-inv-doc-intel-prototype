import pdfplumber
import os
from datetime import datetime, timezone
from app.db.mongo import get_db


def ingest_pdf(file_path: str) -> str:
    
    # error check
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist.")
    
    with pdfplumber.open(file_path) as pdf:

        text_parts = []
        tables = []

        for page in pdf.pages:
            # extract text
            text = page.extract_text()
            if text:
                text_parts.append(text)

            # extract tables
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)

        text = "\n".join(text_parts)

    db = get_db()

    doc = {
    "filename": os.path.basename(file_path),
    "filepath": file_path,
    "raw_text": text,
    "tables": tables,   # list of tables (each table = list of rows)
    "ingest_ts": datetime.now(timezone.utc),
    "status": "ingested",
    "doc_type": None,   # to be filled later by classifier
    "extracted_data": {},
    }

    result = db.documents.insert_one(doc)
    return str(result.inserted_id)
