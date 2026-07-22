#!/bin/bash
# setup-auto-ingest.sh — Create Azure AI Search auto-ingestion pipeline
# Usage: bash scripts/setup-auto-ingest.sh
set -e

# === CONFIG ===
SEARCH_ENDPOINT="https://srch-entchat-poc-sand.search.windows.net"
API_VERSION="2026-04-01"
STORAGE_CONN_STR="DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=staentchatdoc;BlobEndpoint=https://staentchatdoc.blob.core.windows.net/"
OPENAI_ENDPOINT="https://aif-entchat-poc-sand.cognitiveservices.azure.com/"

# NOTE: API keys below are placeholders — replace with current values before running!
SEARCH_KEY="<REPLACE_WITH_SEARCH_KEY>"
OPENAI_KEY="<REPLACE_WITH_OPENAI_KEY>"

HEADERS=(-H "Content-Type: application/json" -H "api-key: $SEARCH_KEY")

echo "============================================"
echo " Azure AI Search — Auto-Ingestion Pipeline"
echo "============================================"

# === 1. DATA SOURCE ===
echo ""
echo "1/4 Creating Data Source..."

curl -s -X PUT "$SEARCH_ENDPOINT/datasources('haadthip-blob-ds')?api-version=$API_VERSION" \
  "${HEADERS[@]}" \
  -d '{
    "name": "haadthip-blob-ds",
    "type": "azureblob",
    "credentials": { "connectionString": "'"$STORAGE_CONN_STR"'" },
    "container": { "name": "documents", "query": "haadthip" }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   ✅ {d[\"name\"]} created')"

# === 2. INDEX ===
echo ""
echo "2/4 Creating Index (vector + semantic)..."

curl -s -X PUT "$SEARCH_ENDPOINT/indexes('haadthip-docs')?api-version=$API_VERSION" \
  "${HEADERS[@]}" \
  -d '{
    "name": "haadthip-docs",
    "fields": [
      { "name": "parent_id",       "type": "Edm.String",          "key": true },
      { "name": "chunk_id",        "type": "Edm.String",          "key": false, "searchable": false, "filterable": true },
      { "name": "content",         "type": "Edm.String",          "searchable": true, "analyzer": "th.microsoft" },
      { "name": "content_vector",  "type": "Collection(Edm.Single)", "dimensions": 3072, "vectorSearchProfile": "hnsw-profile" },
      { "name": "title",           "type": "Edm.String",          "searchable": true,  "filterable": true, "sortable": true },
      { "name": "category",        "type": "Edm.String",          "filterable": true,  "facetable": true },
      { "name": "source_path",     "type": "Edm.String",          "filterable": true },
      { "name": "page_number",     "type": "Edm.Int32",           "filterable": true,  "sortable": true },
      { "name": "chunk_index",     "type": "Edm.Int32",           "filterable": true },
      { "name": "language",        "type": "Edm.String",          "filterable": true,  "facetable": true },
      { "name": "last_updated",    "type": "Edm.DateTimeOffset",  "filterable": true,  "sortable": true }
    ],
    "vectorSearch": {
      "algorithms": [{ "name": "hnsw-algo", "kind": "hnsw", "hnswParameters": { "m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine" } }],
      "profiles": [{ "name": "hnsw-profile", "algorithm": "hnsw-algo" }]
    },
    "semantic": {
      "configurations": [{
        "name": "semantic-default",
        "prioritizedFields": {
          "titleField":    { "fieldName": "title" },
          "contentFields": [{ "fieldName": "content" }],
          "keywordsFields":[{ "fieldName": "category" }]
        }
      }]
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   ✅ {d[\"name\"]} created')"

# === 3. SKILLSET (Split + Embed) ===
echo ""
echo "3/4 Creating Skillset (Split + Embed)..."

curl -s -X PUT "$SEARCH_ENDPOINT/skillsets('haadthip-skillset')?api-version=$API_VERSION" \
  "${HEADERS[@]}" \
  -d '{
    "name": "haadthip-skillset",
    "description": "Split PDFs into chunks and generate embeddings",
    "skills": [
      {
        "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
        "name": "text-split",
        "description": "Split documents into chunks of ~2000 characters with 200 overlap",
        "context": "/document",
        "defaultLanguageCode": "en",
        "textSplitMode": "pages",
        "maximumPageLength": 2000,
        "pageOverlapLength": 200,
        "maximumPagesToTake": 0,
        "inputs": [
          { "name": "text", "source": "/document/content" }
        ],
        "outputs": [
          { "name": "textItems", "targetName": "chunks" }
        ]
      },
      {
        "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
        "name": "embed-chunks",
        "description": "Generate embeddings using text-embedding-3-large (3072 dims)",
        "context": "/document/chunks/*",
        "resourceUri": "'"$OPENAI_ENDPOINT"'",
        "apiKey": "'"$OPENAI_KEY"'",
        "deploymentId": "text-embedding-3-large",
        "modelName": "text-embedding-3-large",
        "dimensions": 3072,
        "inputs": [
          { "name": "text", "source": "/document/chunks/*" }
        ],
        "outputs": [
          { "name": "embedding", "targetName": "vector" }
        ]
      }
    ],
    "indexProjections": {
      "selectors": [
        {
          "targetIndexName": "haadthip-docs",
          "parentKeyFieldName": "parent_id",
          "sourceContext": "/document/chunks/*",
          "mappings": [
            { "name": "chunk_id",      "source": "/document/metadata_storage_name" },
            { "name": "content",       "source": "/document/chunks/*" },
            { "name": "content_vector","source": "/document/chunks/*/vector" },
            { "name": "title",         "source": "/document/metadata_storage_name" },
            { "name": "category",      "source": "/document/metadata_storage_path" },
            { "name": "source_path",   "source": "/document/metadata_storage_path" },
            { "name": "language",      "source": "/document/metadata_storage_content_type" }
          ]
        }
      ]
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   ✅ {d[\"name\"]} created')"

# === 4. INDEXER (with schedule) ===
echo ""
echo "4/4 Creating Indexer (runs every hour, auto-change-detection)..."

curl -s -X PUT "$SEARCH_ENDPOINT/indexers('haadthip-blob-indexer')?api-version=$API_VERSION" \
  "${HEADERS[@]}" \
  -d '{
    "name": "haadthip-blob-indexer",
    "description": "Auto-ingest PDFs from Blob Storage, chunk, embed, and index",
    "dataSourceName": "haadthip-blob-ds",
    "targetIndexName": "haadthip-docs",
    "skillsetName": "haadthip-skillset",
    "schedule": { "interval": "PT1H" },
    "parameters": {
      "batchSize": 1,
      "maxFailedItems": 5,
      "maxFailedItemsPerBatch": 1,
      "configuration": {
        "indexedFileNameExtensions": ".pdf",
        "dataToExtract": "contentAndMetadata",
        "parsingMode": "default",
        "failOnUnsupportedContentType": false,
        "failOnUnprocessableDocument": false
      }
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   ✅ {d[\"name\"]} created')"

echo ""
echo "============================================"
echo " ✅ Pipeline Complete!"
echo "============================================"
echo ""
echo "   Indexer: haadthip-blob-indexer"
echo "   Schedule: Every 1 hour (PT1H)"
echo "   Source:   documents/haadthip/ (19 PDFs)"
echo "   Index:    haadthip-docs"
echo ""
echo "   Check status:"
echo "   curl -s $SEARCH_ENDPOINT/indexers/haadthip-blob-indexer/status?api-version=$API_VERSION -H 'api-key: $SEARCH_KEY' | python3 -m json.tool"
echo ""
echo "   Run now (first time):"
echo "   curl -X POST $SEARCH_ENDPOINT/indexers/haadthip-blob-indexer/run?api-version=$API_VERSION -H 'api-key: $SEARCH_KEY'"
echo ""
