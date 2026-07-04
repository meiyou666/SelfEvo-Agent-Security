param(
    [ValidateSet("mock", "crewai")]
    [string]$AgentBackend = "mock"
)

$ErrorActionPreference = "Stop"

Write-Host "Running attack baseline with backend: $AgentBackend"
python run_attack_scenarios.py --policy baseline --agent-backend $AgentBackend

Write-Host "Running defended dry_run with backend: $AgentBackend"
python run_attack_scenarios.py --policy dry_run --agent-backend $AgentBackend

Write-Host "Generating metrics"
python lab\metrics.py

Write-Host "Generating demo dashboard"
python lab\demo_dashboard.py

Write-Host "Done. Open logs\runs\reports\demo_dashboard.html for the visual demo."
