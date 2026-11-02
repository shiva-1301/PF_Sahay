# Start the backend (:8000) and frontend (:3000) on Windows PowerShell.
# Each server opens in its own window; close the windows to stop them.
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "No .venv found. Run: python -m venv .venv; .venv\Scripts\pip install -r backend\requirements.txt"
    exit 1
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; & '$py' -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev -- --port 3000"
Write-Host "Backend: http://localhost:8000/health   Frontend: http://localhost:3000"
