import json
import logging
import mimetypes
import os
import re
import time
from tempfile import mkdtemp

import azure.functions as func
import magic
import openai
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from flask import Flask, jsonify, request

from .approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from .approaches.readdecomposeask import ReadDecomposeAsk
from .approaches.readretrieveread import ReadRetrieveReadApproach
from .approaches.retrievethenread import RetrieveThenReadApproach
from .cog_services import process_pdf
# Always use relative import for custom module
# from .package.module import MODULE_VALUE

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER") or "content"
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX") or "gptkbindex"
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

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
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
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

# Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
# or some derivative, here we include several for exploration purposes
ask_approaches = {
    "rtr": RetrieveThenReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rrr": ReadRetrieveReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rda": ReadDecomposeAsk(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

app = Flask(__name__)

@app.route("/")
def index():
    return (
        "Try /hello/Chris for parameterized Flask route.\n"
        "Try /module for module import guidance"
    )

@app.route("/api/hello/<name>", methods=['GET'])
def hello(name: str):
    return f"hello {name}"

# Serve content files from blob storage from within the app to keep the example self-contained. 
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@app.route("/api/content/<path>")
def content_file(path):
    blob = blob_container.get_blob_client(path).download_blob()
    mime_type = blob.properties["content_settings"]["content_type"] # type: ignore
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return blob.readall(), 200, {"Content-Type": mime_type, "Content-Disposition": f"inline; filename={path}"}

@app.route("/api/ask", methods=["POST"])
def ask():
    req = request.get_json(silent=True, force=True)
    logging.info(f"ask request: {req}")
    # ensure_openai_token()
    approach = req["approach"] # type: ignore
    try:
        impl = ask_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(req["question"], req["overrides"] or {}) # type: ignore
        logging.info(f"ask response: {r}")
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /ask")
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    req = request.get_json(silent=True, force=True)
    ensure_openai_token()
    approach = req["approach"] # type: ignore
    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(req["history"], req["overrides"] or {}) # type: ignore
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500

@app.route("/api/upload", methods=["POST"]) # type: ignore
def upload():
    req = request
     # Check if files are present in the request
    if not req.files: # type: ignore
        return func.HttpResponse(
             "Please upload at least one file",
             status_code=400
        )
    status = {}
    # Process each file
    for _, file in req.files.items(multi=True): # type: ignore
        file_name = file.filename
        logging.info(f"file_name - {file_name}, file - {file.filename}")        
        # Create a temporary directory to store the uploaded files
        secure_temp_dir = mkdtemp(prefix="az_",suffix="_za")
        base_name, ext = os.path.splitext(os.path.basename(file_name)) # type: ignore
        cleaned_filename = re.sub(r'[ .]', '_', base_name)
        file_to_process = os.path.join(secure_temp_dir, cleaned_filename + ext.lower())
        logging.info(f"base_name - {base_name}, ext - {ext}, cleaned_filename - {cleaned_filename}")
        logging.info(f"file to process - {file_to_process}")
        with open(file_to_process, 'wb') as f:
            file_contents = file.read()
            file_type = magic.from_buffer(file_contents, mime=True)
            f.write(file_contents)
            if file_type == "text/plain":
                logging.info("plain text file")
                logging.info(file_contents.decode("utf-8"))
            elif file_type == "image/png":
                logging.info("png image")
            elif file_type == "image/jpeg":
                logging.info("jpeg image")
            elif file_type == "application/pdf":
                logging.info(f"pdf file - processing - {file_to_process}")
                process_pdf(file_to_process)
            else:
                logging.info("unknown file type")

    logging.info(status)
    return jsonify({ "success":True,"message":"Files processed successfully."}), 200

def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token

if __name__ == "__main__":
    app.run()