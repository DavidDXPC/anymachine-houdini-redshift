# H3 Max image-to-video (fal) for motion reference. Jobs file: { "prefix": "...", "jobs": [ { "out": "x.mp4", "image": "a.png", "prompt": "...", "duration": 8 } ] }
# Paths are relative to this folder. Runs all jobs in parallel. Skips jobs whose output exists unless -Force. Needs $env:FAL_KEY.
param([Parameter(Mandatory)][string]$JobsFile, [switch]$Force, [string[]]$Only = @())
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$cfg = Get-Content (Join-Path $root $JobsFile) -Raw | ConvertFrom-Json
$jobs = foreach ($j in $cfg.jobs) {
  if ($Only.Count -and -not ($Only | ? { $j.out -like "*$_*" })) { continue }
  $dest = Join-Path $root $j.out
  if ((Test-Path $dest) -and -not $Force) { "SKIP $($j.out)"; continue }
  New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
  $img = Join-Path $root $j.image
  $prompt = (@($cfg.prefix, $j.prompt) | ? { $_ }) -join "`n`n"
  $dur = if ($j.duration) { $j.duration } else { 8 }
  Start-Job -ArgumentList $img, $dest, $prompt, $dur -ScriptBlock {
    param($img, $dest, $prompt, $dur)
    $h = @{ Authorization = "Key $env:FAL_KEY"; 'Content-Type' = 'application/json' }
    $uri = 'data:image/png;base64,' + [Convert]::ToBase64String([IO.File]::ReadAllBytes($img))
    $body = @{ prompt = $prompt; image_url = $uri; duration = $dur; resolution = '768P'; prompt_expansion_mode = 'disabled' } | ConvertTo-Json -Depth 4
    try {
      $r = Invoke-RestMethod -Method Post -Headers $h -Body $body -TimeoutSec 1200 -Uri 'https://fal.run/minimax/h3-max/image-to-video'
      Invoke-WebRequest -UseBasicParsing -Uri $r.video.url -OutFile $dest
      "OK $(Split-Path $dest -Leaf)"
    } catch { "FAIL $(Split-Path $dest -Leaf) : $($_.Exception.Message) $($_.ErrorDetails.Message)" }
  }
}
if ($jobs) { $jobs | ? { $_ -is [System.Management.Automation.Job] } | Wait-Job | Receive-Job; $jobs | ? { $_ -is [string] } }
