# Fraud Document Detection

An AI-powered PDF document fraud detection tool built for OCBC's Data Science team. Detects signs of forgery and manipulation in financial documents (e.g. bank statements, payslips) using heuristic analysis of PDF structure, metadata, and content.

## Architecture

```
fraud_doc_detection/
├── backend/          # FastAPI — fraud detection engine
│   └── app/
│       ├── api/      # REST routes
│       ├── models/   # Pydantic schemas
│       └── services/ # Core detection logic (fraud_detector.py)
├── frontend/         # React + TypeScript — analysis UI
│   └── src/
│       ├── components/
│       └── utils/
├── docker-compose.yml
└── start.sh          # Local dev launcher
```

## Detection Checks

The `DocumentFraudDetector` runs the following checks against each uploaded PDF:

| Check | What it looks for |
|---|---|
| **Metadata dates** | Modification date before creation date; implausible date gaps |
| **Creator/producer** | Known image-editing tools (Photoshop, GIMP, Canva) used as PDF creator |
| **Suspicious creator patterns** | Online PDF converters, editors, or unknown tools |
| **Font consistency** | Multiple unrelated font families across a single document |
| **Text layer** | Image-only PDF (no extractable text) — indicates scanned forgery |
| **Transaction patterns** | Weekend/holiday deposits; overly uniform amounts; generic deposit descriptions |
| **Expense keywords** | Absence of expected recurring expenses in bank statements |

Each finding is emitted as a `FraudIndicator` with a severity (`high`, `medium`, `low`, `safe`) and a confidence score (0–100).

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/upload` | Upload a PDF (max 50 MB) |
| `POST` | `/api/analyze/{id}` | Run fraud detection; returns cached result on repeat calls |
| `GET` | `/api/analyze/{id}` | Retrieve cached analysis result |
| `GET` | `/api/documents` | List all uploaded documents with risk summary |
| `GET` | `/api/document/{id}/file` | Serve the original PDF |
| `DELETE` | `/api/document/{id}` | Delete document and results |

Interactive API docs available at `http://localhost:8000/docs` when the backend is running.

## Quick Start

### Option A — shell script (local dev)

```bash
cd src/fraud_doc_detection
chmod +x start.sh
./start.sh
```

This will:
1. Create a Python `venv` and install backend dependencies
2. Start the FastAPI backend on port `8000`
3. Start the Vite dev server (frontend) on port `5173`

Open `http://localhost:5173` in your browser.

### Option B — Docker Compose

```bash
cd src/fraud_doc_detection
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend API | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |

## Backend Setup (manual)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p uploads results
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup (manual)

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

**Backend**
- Python 3.11+
- FastAPI + Uvicorn
- PyMuPDF (`fitz`) — PDF parsing and metadata extraction
- pdfplumber — text and layout extraction
- Pydantic v2 — request/response schemas

**Frontend**
- React 19 + TypeScript
- Vite
- Tailwind CSS v4
- `react-pdf` / `pdfjs-dist` — in-browser PDF rendering
- Axios

## Data Handling

- Uploaded PDFs are stored locally under `backend/uploads/` and never sent to external services.
- Analysis results are cached as JSON under `backend/results/`.
- No customer PII should be present in uploaded documents. If PII is detected in any output, stop immediately and follow the team's data handling protocol.
- Both `uploads/` and `results/` are gitignored.
