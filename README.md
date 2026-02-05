# Apply Agent

Automate LinkedIn Easy Apply using Browser Use. This repo is OS-agnostic and configured with `.env` + `private/` data.

## 1) Requirements
- Python 3.11
- `uv` (`pip install uv`)

## 2) First-time setup
Create the venv:
```bash
uv venv --python 3.11
```

Activate it:
- macOS/Linux: `source .venv/bin/activate`
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`

Install dependencies:
```bash
uv sync
```

## 3) Create your local config
Create `.env`:
```bash
# macOS/Linux
cp .env.example .env
# Windows (PowerShell)
Copy-Item .env.example .env
```

Create `private/` (ignored by git):
```
private/
  resume.pdf
  profile.json
```

Use `profile.example.jsonc` (repo root) as a template for `private/profile.json`.

## 4) Fill in `.env`
Required:
- `PROFILE_JSON_PATH` → path to `private/profile.json`
- `RESUME_PDF_PATH` → path to `private/resume.pdf`

LLM selection:
- Default: `LLM_PROVIDER=google` + `LLM_MODEL=gemini-3-flash-preview`
- Recommended: `LLM_PROVIDER=browser_use` (ChatBrowserUse)
  - Set `BROWSER_USE_API_KEY` if using Browser Use Cloud
- If using Google: set `GOOGLE_API_KEY`

Chrome profile (optional):
- `CHROME_EXECUTABLE_PATH`
- `CHROME_USER_DATA_DIR`
- `CHROME_PROFILE_DIR` (default `Default`)

## 5) Run
```bash
python run.py
```

## Notes
- The script runs headful (`headless=False`).
- `APPLY_NUMBER` controls how many jobs to attempt.
- For best performance in production, use Browser Use Cloud: `LLM_PROVIDER=browser_use` + `BROWSER_USE_API_KEY`.
