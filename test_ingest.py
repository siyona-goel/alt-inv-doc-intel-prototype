from app.ingest.ingest import ingest_pdf
from app.db.mongo import get_db
from bson.objectid import ObjectId

def main():
    # Define file path here
    file_path = "data/Sample-Quarterly-3.pdf"

    # Ingest the sample file
    doc_id = ingest_pdf(file_path)
    print("Ingested with id:", doc_id)

    # Fetch back from Mongo
    db = get_db()
    doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    # Print a preview
    print("\nFilename:", doc["filename"])
    print("\nDoc type:", doc["doc_type"])
    
    # print("\nText preview:", doc["raw_text"][:200], "...")

    # Extracted data
    extracted = doc["extracted_data"]
    print("\nExtracted data:", extracted)

if __name__ == "__main__":
    main()
