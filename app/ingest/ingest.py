import pdfplumber
import os
from datetime import datetime, timezone
from app.db.mongo import get_db
from app.classify.classifier import classify_text
from app.extract.distribution import extract_distribution_fields
from app.extract.capital_call import extract_capital_call_fields
from app.extract.valuation_reports import extract_valuation_fields
from app.extract.quarterly_update import extract_quarterly_update_fields

def ingest_pdf(file_path: str, original_filename: str | None = None) -> str:
    
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
    doc_type = classify_text(text)

    extracted_data = {}
    if doc_type == "distribution_notice":
        extracted_data = extract_distribution_fields(text)
    elif doc_type == "capital_call_letter":
        extracted_data = extract_capital_call_fields(text)
    elif doc_type == "valuation_reports":
        extracted_data = extract_valuation_fields(text)
    elif doc_type == "quarterly_update":
        extracted_data = extract_quarterly_update_fields(text)

    doc = {
    "filename": original_filename or os.path.basename(file_path),
    "filepath": file_path,
    "raw_text": text,
    "tables": tables,                       # list of tables (each table = list of rows)
    "ingest_ts": datetime.now(timezone.utc),
    "status": "ingested",
    "doc_type": doc_type,   
    "extracted_data": extracted_data,
    }

    result = db.documents.insert_one(doc)
    return str(result.inserted_id)
