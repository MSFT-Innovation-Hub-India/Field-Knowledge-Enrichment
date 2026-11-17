using '../main.bicep'

param envName = 'dev'
param containerAppsEnvironmentName = 'pcdotai-agent'
param acrName = 'pcdotaiagentd10b5a'

param searchEndpoint = 'https://ai-search-vector-001.search.windows.net'
param searchResourceGroup = 'ai-search-common-rg'
param searchServiceName = 'ai-search-vector-001'

param foundryResourceGroup = 'rg-foundry-common'
param foundryAccountName = 'ai-foundry-common-ihub'
param foundryProjectEndpoint = 'https://ai-foundry-common-ihub.services.ai.azure.com/api/projects/ihub-project-common'
param foundryOpenAiEndpoint = 'https://ai-foundry-common-ihub.openai.azure.com'

// Supplied by scripts/deploy.ps1 (two-phase first deploy: placeholder image, then the real image).
param image = readEnvironmentVariable('KE_IMAGE', 'mcr.microsoft.com/k8se/quickstart:latest')
param useRegistry = bool(readEnvironmentVariable('KE_USE_REGISTRY', 'false'))
