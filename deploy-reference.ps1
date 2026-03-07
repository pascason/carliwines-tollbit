#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Deploy Podcastify to Azure Container Apps (staging or production).

.PARAMETER Target
  Deployment target: "staging" (default) or "production".
  Staging builds and pushes the staging image, then updates podcastify-staging.
  Production copies the staging image to latest, then updates podcastify.

.PARAMETER Suffix
  Optional revision suffix (e.g. "audio-fix"). Auto-generated if omitted.

.EXAMPLE
  # Deploy to staging (default):
  .\deploy.ps1

  # Deploy to staging with a named revision:
  .\deploy.ps1 -Suffix "topic-fix"

  # Promote staging to production (copies staging image → latest):
  .\deploy.ps1 -Target production
#>
param(
  [ValidateSet("staging", "production")]
  [string]$Target = "staging",
  [string]$Suffix = ""
)

$ErrorActionPreference = "Stop"

$registry     = "podcastifyacr"
$resourceGroup = "rg-podcastify"
$prodApp      = "podcastify"
$stagingApp   = "podcastify-staging"
$prodUrl      = "https://podcastify.redhill-84c315ec.eastus.azurecontainerapps.io"
$stagingUrl   = "https://podcastify-staging.redhill-84c315ec.eastus.azurecontainerapps.io"

if (-not $Suffix) {
  # Auto-generate suffix from git branch + short sha
  $branch = (git rev-parse --abbrev-ref HEAD 2>$null) -replace '[^a-zA-Z0-9-]', ''
  $sha    = (git rev-parse --short HEAD 2>$null)
  $Suffix = "$branch-$sha"
  if ($Suffix.Length -gt 40) { $Suffix = $Suffix.Substring(0, 40) }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Podcastify Deploy → $($Target.ToUpper())" -ForegroundColor Cyan
Write-Host "  Revision suffix:  $Suffix" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($Target -eq "staging") {
  # ── Build & push staging image ──────────────────────────────────
  Write-Host "📦 Building Docker image (tag: staging)..." -ForegroundColor Yellow
  $env:PYTHONIOENCODING = "utf-8"
  az acr build `
    --registry $registry `
    --image "podcastify:staging" `
    --platform linux/amd64 `
    --build-arg "VITE_REDIRECT_URI=$stagingUrl" `
    . --no-logs
  if ($LASTEXITCODE -ne 0) { throw "ACR build failed" }

  Write-Host "🚀 Deploying to $stagingApp..." -ForegroundColor Yellow
  az containerapp update `
    --name $stagingApp `
    --resource-group $resourceGroup `
    --image "$registry.azurecr.io/podcastify:staging" `
    --revision-suffix $Suffix `
    --set-env-vars "AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn"
  if ($LASTEXITCODE -ne 0) { throw "Deploy failed" }

  Write-Host ""
  Write-Host "✅ Deployed to STAGING" -ForegroundColor Green
  Write-Host "   $stagingUrl" -ForegroundColor Green
  Write-Host ""
  Write-Host "Test it, then run:  .\deploy.ps1 -Target production" -ForegroundColor DarkGray

} else {
  # ── Promote staging → production ────────────────────────────────
  Write-Host "⚠️  PROMOTING staging image to PRODUCTION" -ForegroundColor Red
  Write-Host "   This will update the live site at $prodUrl" -ForegroundColor Red
  $confirm = Read-Host "Type 'yes' to continue"
  if ($confirm -ne "yes") {
    Write-Host "Aborted." -ForegroundColor Yellow
    return
  }

  # Re-build with the production redirect URI
  Write-Host "📦 Re-building image with production redirect URI..." -ForegroundColor Yellow
  $env:PYTHONIOENCODING = "utf-8"
  az acr build `
    --registry $registry `
    --image "podcastify:latest" `
    --platform linux/amd64 `
    --build-arg "VITE_REDIRECT_URI=$prodUrl" `
    . --no-logs
  if ($LASTEXITCODE -ne 0) { throw "ACR build failed" }

  Write-Host "🚀 Deploying to $prodApp..." -ForegroundColor Yellow
  az containerapp update `
    --name $prodApp `
    --resource-group $resourceGroup `
    --image "$registry.azurecr.io/podcastify:latest" `
    --revision-suffix $Suffix `
    --set-env-vars "AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn"
  if ($LASTEXITCODE -ne 0) { throw "Deploy failed" }

  Write-Host ""
  Write-Host "✅ Deployed to PRODUCTION" -ForegroundColor Green
  Write-Host "   $prodUrl" -ForegroundColor Green
}
