$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
