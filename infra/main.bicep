// Container App for the Field Knowledge Enrichment POC (resource-group scope).
// Two-phase first deploy: useRegistry=false (placeholder image, identity + roles), then useRegistry=true with the real image.

targetScope = 'resourceGroup'

@description('Environment name, e.g. dev / test / prod. Used in resource and index names.')
param envName string
param location string = resourceGroup().location

param containerAppsEnvironmentName string
param acrName string

@description('Full image reference in the ACR, e.g. myacr.azurecr.io/ke-app:1.0.0')
param image string
@description('false for the first (identity-only) pass with a placeholder image')
param useRegistry bool = true

param searchEndpoint string
param searchResourceGroup string
param searchServiceName string
param searchIndexName string = 'ke-${envName}-knowledge'

param foundryResourceGroup string
param foundryAccountName string
param foundryProjectEndpoint string
param foundryOpenAiEndpoint string
param modelDeployment string = 'gpt-5.4'
param embeddingDeployment string = 'text-embedding-3-small'
param advisorAgentName string = 'sop-advisor-${envName}'
param searchConnectionName string = 'ke-search-entra'

param enrichExistingSops bool = true
param enrichRequireApproval bool = false
param appInsightsConnectionString string = ''

var appName = 'ke-${envName}-app'
var targetPort = useRegistry ? 8000 : 80

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: containerAppsEnvironmentName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false // anonymous access is intentional for the POC; HTTPS only
      }
      registries: useRegistry ? [
        { server: acr.properties.loginServer, identity: 'system' }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'app'
          image: image
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'KE_ENV', value: envName }
            { name: 'FOUNDRY_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
            { name: 'FOUNDRY_OPENAI_ENDPOINT', value: foundryOpenAiEndpoint }
            { name: 'MODEL_DEPLOYMENT', value: modelDeployment }
            { name: 'EMBEDDING_DEPLOYMENT', value: embeddingDeployment }
            { name: 'SEARCH_ENDPOINT', value: searchEndpoint }
            { name: 'SEARCH_INDEX_NAME', value: searchIndexName }
            { name: 'ADVISOR_AGENT_NAME', value: advisorAgentName }
            { name: 'SEARCH_CONNECTION_NAME', value: searchConnectionName }
            { name: 'ENRICH_EXISTING_SOPS', value: string(enrichExistingSops) }
            { name: 'ENRICH_REQUIRE_APPROVAL', value: string(enrichRequireApproval) }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
          ]
          probes: useRegistry ? [
            { type: 'Liveness', httpGet: { path: '/healthz', port: 8000 }, periodSeconds: 30 }
            { type: 'Readiness', httpGet: { path: '/healthz', port: 8000 }, periodSeconds: 10 }
          ] : []
        }
      ]
      // Single replica: in-process locks serialise SOP writes and background jobs must not be killed by scale-to-zero.
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

// ---- role assignments for the Container App's managed identity ----
module acrPull 'modules/acr-role.bicep' = {
  name: 'acr-pull-${envName}'
  params: { acrName: acrName, principalId: app.identity.principalId }
}

module searchRole 'modules/search-role.bicep' = {
  name: 'search-role-${envName}'
  scope: resourceGroup(searchResourceGroup)
  params: { searchServiceName: searchServiceName, principalId: app.identity.principalId }
}

module foundryRole 'modules/foundry-role.bicep' = {
  name: 'foundry-role-${envName}'
  scope: resourceGroup(foundryResourceGroup)
  params: { foundryAccountName: foundryAccountName, principalId: app.identity.principalId }
}

output appName string = app.name
output fqdn string = app.properties.configuration.ingress.fqdn
output principalId string = app.identity.principalId
