param name string
param location string = resourceGroup().location
param tags object = {}

// Reference Properties
@description('Location for Application Insights')
// param applicationInsightsName string = ''
param appServicePlanId string
param formRecognizerService string
param formRecognizerServiceKey string
param azureOpenaiService string
param azureOpenaiServiceKey string
param azureOpenaiChatgptDeployment string
param azureOpenaigptDeployment string
param azureSearchService string
param azureSearchServiceKey string
param azureSearchIndex string
param azureStorageContainerName string

// Microsoft.Web/sites/config
param allowedOrigins array = []
param appCommandLine string = ''
param autoHealEnabled bool = true
param numberOfWorkers int = -1
param ftpsState string = 'FtpsOnly'
param httpsOnly bool = true

@description('Storage Account type')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
])
param storageAccountType string = 'Standard_LRS'

@description('The language worker runtime to load in the function app.')
@allowed([
  'dotnet', 'dotnetcore', 'dotnet-isolated', 'node', 'python', 'java', 'powershell', 'custom'
])
param runtimeName string
param runtimeVersion string
// Microsoft.Web/sites Properties
param kind string = 'functionapp'

var storageAccountName = '${uniqueString(resourceGroup().id)}azfunctions'

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageAccountType
  }
  kind: 'Storage'
  properties: {
    supportsHttpsTrafficOnly: true
    defaultToOAuthAuthentication: true
  }
}

resource functionApp 'Microsoft.Web/sites@2021-03-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlanId
    siteConfig: {
      linuxFxVersion: '${toUpper(runtimeName)}|${runtimeVersion}'
      appCommandLine: appCommandLine
      numberOfWorkers: numberOfWorkers != -1 ? numberOfWorkers : null
      autoHealEnabled: autoHealEnabled
      pythonVersion: runtimeVersion
      cors: {
        allowedOrigins: union([ 'https://portal.azure.com', 'https://ms.portal.azure.com' ], allowedOrigins)
      }
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: runtimeName
        }
        // {
        //   name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
        //   value: applicationInsights.properties.InstrumentationKey
        // }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'AZURE_FORM_RECOGNIZER_SERVICE'
          value: formRecognizerService
        }
        {
          name: 'AZURE_FORM_RECOGNIZER_KEY'
          value: formRecognizerServiceKey
        }
        {
          name: 'AZURE_OPENAI_SERVICE'
          value: azureOpenaiService
        }
        {
          name: 'AZURE_OPENAI_CHATGPT_DEPLOYMENT'
          value: azureOpenaiChatgptDeployment
        }
        {
          name: 'AZURE_OPENAI_GPT_DEPLOYMENT'
          value: azureOpenaigptDeployment
        }
        {
          name: 'AZURE_SEARCH_SERVICE'
          value: azureSearchService
        }
        {
          name: 'AZURE_SEARCH_KEY'
          value: azureSearchServiceKey
        }
        {
          name: 'AZURE_SEARCH_INDEX'
          value: azureSearchIndex
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: azureOpenaiServiceKey
        }
        {
          name: 'AZURE_STORAGE_CONTAINER'
          value: azureStorageContainerName
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT'
          value: storageAccountName
        }
      ]
      ftpsState: ftpsState
      minTlsVersion: '1.2'
    }
    httpsOnly: httpsOnly
  }
}

output id string = functionApp.id
output identityPrincipalId string = functionApp.identity.principalId
output name string = functionApp.name
