$backendRoot = 'D:\maritime_web_codex\backend'
$frontendRoot = 'D:\maritime_web_codex\frontend'

$env:MARITIME_AUTOSTART_MICROSERVICES = "1"
$backendHost = if ($env:MARITIME_BACKEND_HOST) { $env:MARITIME_BACKEND_HOST } else { "127.0.0.1" }
$backendPort = if ($env:MARITIME_BACKEND_PORT) { $env:MARITIME_BACKEND_PORT } else { "8000" }

Write-Host "Starting backend orchestrator..." -ForegroundColor Cyan
$apiArgs = @("-m", "uvicorn", "main:app", "--host", $backendHost, "--port", $backendPort, "--reload")
Start-Process -FilePath "python" -WorkingDirectory $backendRoot -ArgumentList $apiArgs -NoNewWindow

Write-Host "Waiting for backend health..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
  try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://$backendHost`:$backendPort/health" -TimeoutSec 2 | Out-Null
    break
  } catch {
    Start-Sleep -Milliseconds 500
  }
}

Write-Host "Starting frontend..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -WorkingDirectory $frontendRoot -ArgumentList "/c", "npm", "run", "dev" -NoNewWindow

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Backend, microservices, and frontend are starting." -ForegroundColor Green
Write-Host "The backend now auto-discovers and launches the service registry." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
