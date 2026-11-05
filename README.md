# Accel Business — Udyam Digital

**Track A · Accel YTL Hackathon 2026**
*Making small businesses go digital in one sitting*

---

## Quick Start (One Command)

### Option 1: Docker Compose
\\ash
docker compose up
\
### Option 2: Local Run
\\ash
# Terminal 1: Backend
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
\
- **Frontend App:** http://localhost:5173
- **Back-Office Portal:** http://localhost:5173/office
- **FastAPI OpenAPI Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## Quality Bar & Tests

Run all 47 automated backend tests:
\\ash
cd backend
.\.venv\Scripts\pytest.exe -v
\
Frontend build:
\\ash
cd frontend
npm run build
\