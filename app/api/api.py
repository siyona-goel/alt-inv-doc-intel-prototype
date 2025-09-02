from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import tempfile
from bson import ObjectId
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.ingest.ingest import ingest_pdf
from app.db.mongo import get_db

app = FastAPI(
    title="Alternative Investments Document Intelligence API",
    description="API for processing and extracting data from investment documents",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class DocumentResponse(BaseModel):
    id: str
    filename: str
    doc_type: str
    ingest_ts: datetime
    extracted_data: Dict[str, Any]

class DocumentListResponse(BaseModel):
    id: str
    filename: str
    doc_type: str
    ingest_ts: datetime

class UploadResponse(BaseModel):
    document_id: str
    message: str

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Document Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "document": "/document/{document_id}",
            "documents": "/documents",
            "docs": "/docs"
        }
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document for processing and extraction.
    
    - **file**: PDF file to upload and process
    - Returns the inserted document ID
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    tmp_path = None
    try:
        # Write the uploaded file content to a closed temp file (Windows requires closed handle)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            tmp_path = temp_file.name

        # process the document
        document_id = ingest_pdf(tmp_path, original_filename=file.filename)

        return UploadResponse(
            document_id=document_id,
            message=f"Document '{file.filename}' processed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        # Ensure temp file is removed, ignoring errors if already deleted or locked
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

@app.get("/document/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """
    Retrieve a document by its ID.
    
    - **document_id**: The MongoDB ObjectId of the document
    - Returns the full document with extracted data
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(document_id):
            raise HTTPException(status_code=400, detail="Invalid document ID format")
        
        # Get document from MongoDB
        db = get_db()
        document = db.documents.find_one({"_id": ObjectId(document_id)})
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Convert ObjectId to string for JSON serialization
        document["id"] = str(document["_id"])
        del document["_id"]
        
        return DocumentResponse(**document)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

@app.get("/documents", response_model=List[DocumentListResponse])
async def list_documents(
    limit: Optional[int] = 100,
    skip: Optional[int] = 0,
    doc_type: Optional[str] = None
):
    
    # List documents with optional filtering and pagination.
    
    # **limit**: Maximum number of documents to return (default: 100, max: 1000)
    # **skip**: Number of documents to skip for pagination (default: 0)
    # **doc_type**: Filter by document type (optional)
    # Returns list of documents with basic information
    
    try:
        # Validate parameters
        if limit > 1000:
            limit = 1000
        if limit < 1:
            limit = 1
        if skip < 0:
            skip = 0
        
        # Build query
        query = {}
        if doc_type:
            query["doc_type"] = doc_type
        
        # Get documents from MongoDB
        db = get_db()
        cursor = db.documents.find(
            query,
            {"filename": 1, "doc_type": 1, "ingest_ts": 1}
        ).sort("ingest_ts", -1).skip(skip).limit(limit)
        
        documents = []
        for doc in cursor:
            documents.append(DocumentListResponse(
                id=str(doc["_id"]),
                filename=doc["filename"],
                doc_type=doc["doc_type"],
                ingest_ts=doc["ingest_ts"]
            ))
        
        return documents
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = get_db()
        db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
