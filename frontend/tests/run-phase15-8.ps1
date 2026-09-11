$ErrorActionPreference = "Continue"

function Ensure-Http($Url, $Name) {
  for ($i = 0; $i -lt 40; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
    } catch { }
    Start-Sleep -Seconds 2
  }
  return $false
}

# --- Backend ---
$beUp = $false
try { $beUp = (Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { }
if (-not $beUp) {
  Write-Output "[runner] starting backend..."
  Start-Process -FilePath "C:\Users\BILALH~1\AppData\Local\Temp\opencode\be.bat" -WindowStyle Hidden -PassThru | Out-Null
  if (-not (Ensure-Http "http://127.0.0.1:8000/api/health" "backend")) { Write-Output "[runner] BACKEND FAILED TO START"; exit 1 }
}
Write-Output "[runner] backend OK"

# --- Frontend ---
$feUp = $false
try { $feUp = (Invoke-WebRequest -Uri "http://localhost:3000/" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { }
if (-not $feUp) {
  Write-Output "[runner] starting frontend..."
  Start-Process -FilePath "C:\Users\BILALH~1\AppData\Local\Temp\opencode\fe.bat" -WindowStyle Hidden -PassThru | Out-Null
  if (-not (Ensure-Http "http://localhost:3000/" "frontend")) { Write-Output "[runner] FRONTEND FAILED TO START"; exit 1 }
}
Write-Output "[runner] frontend OK"

# --- Chrome (CDP 9230) ---
$chromeUp = $false
try { $chromeUp = (Invoke-WebRequest -Uri "http://127.0.0.1:9230/json/version" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { }
if (-not $chromeUp) {
  Write-Output "[runner] starting chrome..."
  $chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
  if (-not (Test-Path $chrome)) { $chrome = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe" }
  $prof = "C:\Users\BILALH~1\AppData\Local\Temp\opencode\cdp15-8-profile"
  Start-Process -FilePath $chrome -ArgumentList @("--headless=new", "--remote-debugging-port=9230", "--user-data-dir=$prof", "--no-first-run", "--no-default-browser-check", "--disable-gpu", "about:blank") -WindowStyle Hidden -PassThru | Out-Null
  if (-not (Ensure-Http "http://127.0.0.1:9230/json/version" "chrome")) { Write-Output "[runner] CHROME FAILED TO START"; exit 1 }
}
Write-Output "[runner] chrome OK"

# --- Reset seats / remove test bookings (clean start state) ---
python "C:\Users\BILALH~1\AppData\Local\Temp\opencode\reset-seats.py"
Write-Output "[runner] seats reset OK"

# --- Run E2E ---
Write-Output "[runner] running E2E..."
node "D:\OPENAI_AGENT_SDK\flight_assistant\frontend\tests\phase15-8-e2e.mjs"
$code = $LASTEXITCODE
Write-Output "[runner] E2E exit code: $code"
exit $code