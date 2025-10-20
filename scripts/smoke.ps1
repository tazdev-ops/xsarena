# PowerShell smoke test (Windows)
$ErrorActionPreference = "Stop"

Write-Host "== XSArena smoke test =="

# 1) CLI basics
xsarena version | Out-Null
xsarena --help | Out-Null
xsarena --backend bridge --model default --window 42 settings show | Out-Null

# 2) Bridge up (start non-blocking)
Start-Process -FilePath "xsarena" -ArgumentList "ops","service","start-bridge-v2" | Out-Null
Start-Sleep -Seconds 1

# Wait for health
$ok = $false
for ($i=0; $i -lt 40; $i++) {
  try {
    $resp = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5102/v1/health
    if ($resp.Content -match '"status":"ok"') { $ok = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 500
}
if (-not $ok) { throw "Bridge health failed" }

# 3) Offline simulate
xsarena dev simulate "Sanity Subject" --length standard --span medium | Out-Null
xsarena ops jobs ls | Out-Null

# 4) Dry-run
xsarena run book "Sanity Subject" --dry-run | Out-Null

# 5) Continue
New-Item -ItemType Directory -Force -Path .\books | Out-Null
"# Test" | Set-Content .\books\Resume_Test.final.md
xsarena run continue .\books\Resume_Test.final.md --length standard --span medium --no-wait | Out-Null

# 6) Docs
xsarena docs gen-help | Out-Null
if (-not (Test-Path .\docs\_help_root.txt)) { throw "docs root help missing" }

Write-Host "== OK =="
