<#
 Assigns the cross-resource roles the solution needs (Entra only, no keys). Idempotent.
 Requires Owner / User Access Administrator on the scopes. Container App roles are assigned by deploy.ps1.
 Usage: ./scripts/assign-roles.ps1 -Subscription <id>
#>
param(
  [string]$Subscription = "bc2e2415-164d-45a5-9a4a-29d9264a343e",
  [string]$SearchRg = "ai-search-common-rg",   [string]$SearchName = "ai-search-vector-001",
  [string]$FoundryRg = "rg-foundry-common",    [string]$FoundryAccount = "ai-foundry-common-ihub",
  [string]$FoundryProject = "ihub-project-common"
)
$ErrorActionPreference = "Stop"
$searchId  = "/subscriptions/$Subscription/resourceGroups/$SearchRg/providers/Microsoft.Search/searchServices/$SearchName"
$foundryId = "/subscriptions/$Subscription/resourceGroups/$FoundryRg/providers/Microsoft.CognitiveServices/accounts/$FoundryAccount"

$searchMi  = az resource show --ids $searchId --query identity.principalId -o tsv
$projectMi = az resource show --ids "$foundryId/projects/$FoundryProject" --query identity.principalId -o tsv

function Grant($principal, $role, $scope) {
  az role assignment create --assignee-object-id $principal --assignee-principal-type ServicePrincipal --role $role --scope $scope -o none 2>$null
  Write-Host "  $role -> $scope"
}

Write-Host "Foundry project MI -> Search (agent knowledge tool)"
Grant $projectMi "Search Index Data Reader"   $searchId
Grant $projectMi "Search Service Contributor" $searchId
Write-Host "Search MI -> Foundry (index vectorizer)"
Grant $searchMi "Cognitive Services OpenAI User" $foundryId
