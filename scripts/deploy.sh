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
func azure functionapp publish $AZURE_FUNCTION_NAME