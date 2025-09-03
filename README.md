# Alternative Investments Document Intelligence

A FastAPI-based system for processing and extracting data from investment documents (PDFs).

## Features

- **Document Classification**: AI-powered classification of investment documents
- **Data Extraction**: Automated extraction of key fields from different document types
- **MongoDB Storage**: Persistent storage of documents and extracted data
- **RESTful API**: FastAPI endpoints for document management

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the API

### Start the FastAPI server:

```bash
uvicorn app.api.api:app --reload --host 0.0.0.0 --port 8000
```

### Alternative: Run directly with Python:

```bash
python -m app.api.api
```

## API Endpoints

- **GET /** - API information and available endpoints
- **POST /upload** - Upload and process a PDF document
- **GET /document/{document_id}** - Retrieve a document by ID
- **GET /documents** - List documents with optional filtering
- **GET /health** - Health check endpoint
- **GET /docs** - Interactive API documentation (Swagger UI)

## Usage Examples

### Upload a document:
```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_document.pdf"
```

### List documents:
```bash
curl "http://localhost:8000/documents?limit=10&doc_type=quarterly_update"
```

### Get a specific document:
```bash
curl "http://localhost:8000/document/68b5d2b3c68683db104b6e58"
```

## Testing

Run the test script to verify API functionality:
```bash
python test_api.py
```

## Development

- The API uses FastAPI with automatic request/response validation
- MongoDB integration for document storage
- Built-in Swagger UI at `/docs` for API exploration
- Proper error handling and HTTP status codes