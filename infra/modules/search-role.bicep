param searchServiceName string
param principalId string

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

// Search Index Data Contributor: read and write documents (data plane only, no schema changes)
var indexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

resource assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, principalId, indexDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', indexDataContributorRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
