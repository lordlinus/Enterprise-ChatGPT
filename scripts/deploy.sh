#!/bin/bash

output=$(azd env get-values)

while IFS= read -r line; do
    name=$(echo "$line" | cut -d'=' -f1)
    value=$(echo "$line" | cut -d'=' -f2- | sed 's/^"\|"$//g')
    export "$name"="$value"
done <<< "$output"

echo "Environment variables set."

cd ./app/frontend
SWA_DEPLOYMENT_TOKEN=$(az staticwebapp secrets list --name $AZURE_STATICWEBSITE_NAME --query "properties.apiKey" --output tsv)
swa deploy --deployment-token $SWA_DEPLOYMENT_TOKEN

cd ../backend
AZURE_FORM_RECOGNIZER_KEY=$(az cognitiveservices account keys list --name $AZURE_FORMRECOGNIZER_SERVICE --resource-group $AZURE_RESOURCE_GROUP --query "key1" --output tsv)
AZURE_OPENAI_API_KEY=$(az cognitiveservices account keys list --name $AZURE_OPENAI_SERVICE --resource-group $AZURE_RESOURCE_GROUP --query "key1" --output tsv)
AZURE_SEARCH_KEY=$(az cognitiveservices account keys list --name $AZURE_SEARCH_SERVICE --resource-group $AZURE_RESOURCE_GROUP --query "key1" --output tsv)
func azure functionapp publish $AZURE_FUNCTION_NAME