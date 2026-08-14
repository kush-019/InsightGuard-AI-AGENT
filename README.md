# InsightGuard — Frontend + Python Engine Integration

This package connects the red/black InsightGuard dashboard to the existing generic Python anomaly engine.

## Architecture

Browser (Next.js)
→ FastAPI
→ data_profiler.py
→ generic_analyzer.py
→ historical_analyzer.py
→ Gemini AI
→ Resend consolidated email

The Python engine automatically detects the date column and numeric business metrics. It is not locked to Revenue/Orders/etc.

## 1. Backend

Open PowerShell in `backend`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` from `.env.example` and add:

```text
GEMINI_API_KEY=your_key
RESEND_API_KEY=your_key
RESEND_FROM_EMAIL=your_verified_sender
FRONTEND_ORIGIN=http://localhost:3000
```

Start:

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Health check:

`http://127.0.0.1:8000/api/health`

## 2. Frontend

Open another PowerShell in `insightguard-web`:

```powershell
npm install
```

Copy `.env.local.example` to `.env.local`:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## What now works

- Upload `.xlsx`, `.xls`, or `.csv`
- Automatic date-column detection
- Automatic metric detection
- Complete historical anomaly analysis
- Critical-date timeline
- Critical-date selector
- Gemini analysis for selected incident
- Consolidated report email to the user's entered Gmail address
- One email for all critical dates
- Dashboard navigation buttons
- Analyze New File
- Responsive mobile sidebar

## Important deployment architecture

For production, deploy the Next.js frontend to Vercel and deploy this FastAPI backend to a Python host such as Render/Railway. Set `NEXT_PUBLIC_API_URL` on Vercel to the public backend URL and set the backend CORS `FRONTEND_ORIGIN` to the Vercel URL.

Do not put `GEMINI_API_KEY` or `RESEND_API_KEY` in the Next.js frontend.
