# AI Timesheet Processor

Web app that reads a monthly handwritten timesheet PDF, matches employees to
a master Excel payroll workbook by IQAMA/Passport number, and writes the
confirmed hours into the right day columns — without touching existing
formulas or formatting.

## Prerequisites

- Python 3.11 or 3.12
- Node.js 18+
- Tesseract OCR (Windows): https://github.com/UB-Mannheim/tesseract/wiki

## Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Generate your admin password hash:

```powershell
python scripts\generate_password_hash.py
```

Copy the printed `AUTH_PASSWORD_HASH=...` line into `.env`. Also set a random
`JWT_SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Confirm Tesseract is installed at the path in `.env` (`TESSERACT_CMD`):

```powershell
Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Run the backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Check http://localhost:8000/api/health → `{"status":"ok"}`
API docs: http://localhost:8000/docs

## Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5173

## Environment variables

**backend/.env**
| Variable | Purpose |
|---|---|
| `AUTH_USERNAME` | The single admin username |
| `AUTH_PASSWORD_HASH` | bcrypt hash, generated via the script above |
| `JWT_SECRET_KEY` | Random secret for signing tokens |
| `OCR_ENGINE` | `tesseract` (default); swap engines here later |
| `TESSERACT_CMD` | Path to tesseract.exe |
| `STORAGE_DIR` | Where temp uploads/sessions are stored |

**frontend/.env**
| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend URL, e.g. `http://localhost:8000` |

## Known limitations (by design, per spec)

- Single admin user, no database, no self-signup/password reset
- No payroll/overtime calculation, analytics, or multilingual support
- Handwriting OCR runs on free Tesseract by default — accuracy on messy
  handwriting is inconsistent, which is why manual review is mandatory
- Large PDFs (hundreds of employees) can take a few minutes to process;
  there's a single request/response cycle with no intermediate progress
  polling, per the fixed API contract