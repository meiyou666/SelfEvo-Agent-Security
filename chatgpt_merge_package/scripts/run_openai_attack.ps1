$ErrorActionPreference = "Stop"

Write-Host "Running OpenAI / ChatGPT attack comparison..."

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating .venv..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Running tests..."
.\.venv\Scripts\python.exe -m unittest discover -v

Write-Host "Running OpenAI baseline..."
.\.venv\Scripts\python.exe run_attack_scenarios.py --policy baseline --agent-backend crewai

Write-Host "Running OpenAI dry_run defense..."
.\.venv\Scripts\python.exe run_attack_scenarios.py --policy dry_run --agent-backend crewai

Write-Host "Generating metrics..."
.\.venv\Scripts\python.exe lab\metrics.py

Write-Host "Done. Check logs\runs and logs\runs\reports."
