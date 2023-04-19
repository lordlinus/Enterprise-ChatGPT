import os
import time

import openai
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from langchain.llms.openai import AzureOpenAI
from langchain.utilities import BingSearchAPIWrapper

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get(
    "AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get(
    "AZURE_STORAGE_CONTAINER") or "content"
AZURE_STORAGE_KEY = os.environ.get("AZURE_STORAGE_KEY") or None
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX") or "gptkbindex"
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY") or None
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"
AZURE_FORM_RECOGNIZER_SERVICE = os.environ.get(
    "AZURE_FORM_RECOGNIZER_SERVICE") or "myformrecognizer"
AZURE_FORM_RECOGNIZER_KEY = os.environ.get("AZURE_FORM_RECOGNIZER_KEY") or None
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID") or None
LOCAL_PDF_PARSER_BOOL = os.environ.get("LOCAL_PDF_PARSER_BOOL") or False
LOG_VERBOSE = os.environ.get("LOG_VERBOSE") or False

# The default category to use if none is specified
AZURE_OPENAI_DEFAULT_TEMP = os.environ.get("AZURE_OPENAI_DEFAULT_TEMP") or 0.3

CATEGORY = os.environ.get("CATEGORY") or "default"

MAX_SECTION_LENGTH = 1000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100


KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

BING_SUBSCRIPTION_KEY = os.environ.get("BING_SUBSCRIPTION_KEY") or ""
BING_SEARCH_URL = os.environ.get("BING_SEARCH_URL") or 'https://api.bing.microsoft.com/v7.0/search'

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed,
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential()

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2022-12-01"

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token(
    "https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)
blob_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=azure_credential)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

default_creds = azure_credential if AZURE_STORAGE_KEY == None else AzureKeyCredential(
    AZURE_STORAGE_KEY)
search_creds = azure_credential if AZURE_SEARCH_KEY == None else AzureKeyCredential(
    AZURE_SEARCH_KEY)
formrecognizer_creds = azure_credential if AZURE_FORM_RECOGNIZER_KEY == None else AzureKeyCredential(
    AZURE_FORM_RECOGNIZER_KEY)

# bing_search_client = BingSearchAPIWrapper(bing_subscription_key=BING_SUBSCRIPTION_KEY, bing_search_url=BING_SEARCH_URL)
# llm_gpt = AzureOpenAI(deployment_name=f"{AZURE_OPENAI_GPT_DEPLOYMENT}", temperature=f"{AZURE_OPENAI_DEFAULT_TEMP}", openai_api_key=openai_token) # type: ignore
# llm_chat = AzureOpenAI(deployment_name=f"{AZURE_OPENAI_GPT_DEPLOYMENT}", temperature=f"{AZURE_OPENAI_DEFAULT_TEMP}", openai_api_key=openai_token) # type: ignore


def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token(
            "https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
