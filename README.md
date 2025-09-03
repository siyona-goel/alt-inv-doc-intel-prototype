# Alternative Investments Document Intelligence

## Setup
### Prerequisites
- Python 3.11+<br/>
- Node.js 18+<br/>
- npm<br/>
- MongoDB (local install) or Docker (for a containerized setup)

### 1. Clone the repository
   ```bash
   git clone https://github.com/<your-username>/alt-inv-doc-intel-prototype.git
   cd alt-inv-doc-intel-prototype
   ```
### 2. Local Development
   ### Backend (FastAPI)
   1. Create and activate virtual environment
      ```bash
      python -m venv venv
      source venv/bin/activate   # macOS/Linux
      venv\Scripts\activate      # Windows
      ```
   2. Install dependencies:
      ```bash
      pip install -r requirements.txt
      ```
   3. Start MongoDB (if it's not running already):
      ```bash
      mongod --dbpath /path/to/your/mongo/data
      ```
   4. Run backend:
      ```bash
      uvicorn app.api.api:app --reload --port 8000
      ```
      The API will be available at: http://localhost:8000

   ### Frontend (React + Vite)
   1. Go to frontend directory:
      ```bash
      cd frontend
      ```
   2. Install dependencies:
      ```bash
      npm install
      ```
   3. Start the dev server:
      ```bash
      npm run dev
      ```
      The UI will be available at: http://localhost:5173

### 3. Dockerized Setup
   1. Ensure Docker & Docker Compose are installed.
   2. From project root, build and start all services:
      ```bash
      docker compose up --build
      ```
      This runs:
      - MongoDB at localhost:27017
      - Backend API at http://localhost:8000
      - Frontend UI at http://localhost:3000
   3. Stop services:
      ```bash
      docker compose down
      ```

## Usage 
1. Open http://localhost:3000 in your browser.
2. Upload a financial PDF document.
3. The system will classify the document and extract fields.
4. Results are displayed in the UI and stored in MongoDB.
