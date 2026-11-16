# GPT Image 2.6 edit (sunburst) with reference images. Jobs file: { "prefix": "...", "jobs": [ { "out": "x.png", "refs": ["a.png"], "prompt": "...", "size": "landscape_16_9" } ] }
# Paths in refs/out are relative to this folder. Runs all jobs in parallel. Skips jobs whose output already exists unless -Force.
param([Parameter(Mandatory)][string]$JobsFile, [switch]$Force, [string[]]$Only = @())
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$cfg = Get-Content (Join-Path $root $JobsFile) -Raw | ConvertFrom-Json
$jobs = foreach ($j in $cfg.jobs) {
  if ($Only.Count -and -not ($Only | ? { $j.out -like "*$_*" })) { continue }
  $dest = Join-Path $root $j.out
  if ((Test-Path $dest) -and -not $Force) { "SKIP $($j.out)"; continue }
  New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
  $refs = @($j.refs | % { Join-Path $root $_ })
  $prompt = (@($cfg.prefix, $j.prompt) | ? { $_ }) -join "`n`n"
  $size = if ($j.size) { $j.size } else { 'auto' }
  Start-Job -ArgumentList $refs, $dest, $prompt, $size -ScriptBlock {
    param($refs, $dest, $prompt, $size)
    $uris = @($refs | % { 'data:image/png;base64,' + [Convert]::ToBase64String([IO.File]::ReadAllBytes($_)) })
    $h = @{ Authorization = "Key $env:FAL_KEY"; 'Content-Type' = 'application/json' }
    $body = @{ prompt = $prompt; image_urls = $uris; num_images = 1; image_size = $size; quality = 'high' } | ConvertTo-Json -Depth 4
    try {
      $r = Invoke-RestMethod -Method Post -Headers $h -Body $body -TimeoutSec 1200 -Uri 'https://fal.run/openai/gpt-image-2.6/sunburst/edit'
      Invoke-WebRequest -UseBasicParsing -Uri $r.images[0].url -OutFile $dest
      "OK $(Split-Path $dest -Leaf)"
    } catch { "FAIL $(Split-Path $dest -Leaf) : $($_.Exception.Message) $($_.ErrorDetails.Message)" }
  }
}
if ($jobs) { $jobs | ? { $_ -is [System.Management.Automation.Job] } | Wait-Job | Receive-Job; $jobs | ? { $_ -is [string] } }
