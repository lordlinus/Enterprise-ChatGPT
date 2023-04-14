#!/bin/bash

output=$(azd env get-values)

while IFS= read -r line; do
    name=$(echo "$line" | cut -d'=' -f1)
    value=$(echo "$line" | cut -d'=' -f2- | sed 's/^"\|"$//g')
    export "$name"="$value"
done <<< "$output"

echo "Environment variables set."

az account set --subscription $AZURE_SUBSCRIPTION_ID

cd ./app/frontend
SWA_DEPLOYMENT_TOKEN=$(az staticwebapp secrets list --name $AZURE_STATICWEBSITE_NAME --query "properties.apiKey" --output tsv)
swa deploy --env production --deployment-token $SWA_DEPLOYMENT_TOKEN

cd ../backend
# AZURE_FORM_RECOGNIZER_KEY=$(az cognitiveservices account keys list --name $AZURE_FORMRECOGNIZER_SERVICE --resource-group $AZURE_RESOURCE_GROUP --query "key1" --output tsv)
# AZURE_OPENAI_API_KEY=$(az cognitiveservices account keys list --name $AZURE_OPENAI_SERVICE --resource-group $AZURE_RESOURCE_GROUP --query "key1" --output tsv)
AZURE_SEARCH_KEY=$(az cognitiveservices account keys list --name $AZURE_SEARCH_SERVICE --resource-group $AZURE_RESOURCE_GROUP --query "key1" --output tsv)
az functionapp config appsettings list --name $AZURE_FUNCTION_NAME --resource-group $AZURE_RESOURCE_GROUP --settings AZURE_SEARCH_KEY=$AZURE_SEARCH_KEY
func azure functionapp publish $AZURE_FUNCTION_NAME

# Purge a deleted resource
# az resource delete --ids /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$AZURE_FORMRECOGNIZER_SERVICE
# az resource delete --ids /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$AZURE_SEARCH_SERVICE

# recover
# az cognitiveservices account recover --location $AZURE_LOCATION --name $AZURE_FORMRECOGNIZER_SERVICE --resource-group $AZURE_RESOURCE_GROUP
# az cognitiveservices account recover --location eastus --name cog-y2nmeuebipp4i --resource-group $AZURE_RESOURCE_GROUP
# az cognitiveservices account delete --location $AZURE_LOCATION --name cog-y2nmeuebipp4i --resource-group $AZURE_RESOURCE_GROUP