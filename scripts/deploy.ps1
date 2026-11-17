<#
 Build the image in ACR (no local Docker) and deploy the Container App for an environment.
 Usage: ./scripts/deploy.ps1 -Env dev
 Prerequisites: az login; Owner / User Access Administrator on the scopes (role assignments are part of the template).
 One-time per environment, after the first deploy: run tools/bootstrap_index.py and tools/create_agent.py
 (see README) and ./scripts/assign-roles.ps1.
#>
param(
  [string]$Env = "dev",
  [string]$ResourceGroup = "pcdotai-agent",
  [string]$AcrName = "pcdotaiagentd10b5a",
  [string]$Tag = (Get-Date -Format "yyyyMMddHHmmss")
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$appName = "ke-$Env-app"
$paramFile = Join-Path $root "infra/params/$Env.bicepparam"
$template = Join-Path $root "infra/main.bicep"
$image = "$AcrName.azurecr.io/ke-app:$Tag"

function Deploy($useRegistry, $img) {
  $env:KE_USE_REGISTRY = $useRegistry
  $env:KE_IMAGE = $img
  az deployment group create -g $ResourceGroup -n "ke-$Env-$(Get-Date -Format HHmmss)" -f $template -p $paramFile --query "properties.outputs" -o json
  if ($LASTEXITCODE -ne 0) { throw "Deployment failed" }
}

# Phase 1: identity + role assignments (only if the app does not exist yet)
$exists = az containerapp show -g $ResourceGroup -n $appName --query name -o tsv 2>$null
if (-not $exists) {
  Write-Host "Phase 1: creating app identity and role assignments with a placeholder image..."
  Deploy "false" "mcr.microsoft.com/k8se/quickstart:latest" | Out-Null
  Write-Host "Waiting for role assignments to propagate..."
  Start-Sleep -Seconds 60
}

Write-Host "Building $image in ACR $AcrName (cloud build)..."
az acr build -r $AcrName -t "ke-app:$Tag" -f (Join-Path $root "Dockerfile") $root --no-logs -o none 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { throw "az acr build failed" }

Write-Host "Phase 2: deploying the application image..."
$out = Deploy "true" $image | ConvertFrom-Json
$fqdn = $out.fqdn.value
Write-Host "App URL: https://$fqdn"
Start-Sleep -Seconds 20
try { Invoke-RestMethod "https://$fqdn/healthz" | ConvertTo-Json } catch { Write-Warning "Health check not ready yet: $($_.Exception.Message)" }
