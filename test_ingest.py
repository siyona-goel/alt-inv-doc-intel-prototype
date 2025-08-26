from app.ingest.ingest import ingest_pdf
from app.db.mongo import get_db
from bson.objectid import ObjectId

def main():
    # Ingest the sample file
    doc_id = ingest_pdf("data/Sample-Capital-Call-Letter.pdf")
    print("Ingested with id:", doc_id)

    # Fetch back from Mongo
    db = get_db()
    doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    # Print a preview
    print("Filename:", doc["filename"])
    print("Doc type:", doc["doc_type"])
    # print("Status:", doc["status"])
    print("Text preview:", doc["raw_text"][:200], "...")
    # print("Number of tables extracted:", len(doc.get("tables", [])))
    print("Extracted data:", doc["extracted_data"])

if __name__ == "__main__":
    main()
