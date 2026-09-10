#!/usr/bin/env bash
# Test whether the app's client-credentials token can access Fabric (Power BI)
# workspaces/items — in particular the workspace cbcec8c4-c2c9-4e7c-88da-5c20aa21142c.
# NOTE: reads secrets from EnterpriseChat/.env — never prints them.
set -euo pipefail

ENV_FILE="/Users/supakorn.emch/Workspace/Haadthip/EnterpriseChat/.env"
# shellcheck disable=SC1090
source "$ENV_FILE"

TENANT="$MICROSOFT_CLIENT_TENANT_ID"
CID="$MICROSOFT_CLIENT_ID"
CSEC="$MICROSOFT_CLIENT_SECRET"

WS_ID="cbcec8c4-c2c9-4e7c-88da-5c20aa21142c"

get_token() {
  local scope="$1" out="$2"
  local code
  code=$(curl -s -o "$out" -w "%{http_code}" \
    -X POST "https://login.microsoftonline.com/${TENANT}/oauth2/v2.0/token" \
    -d "client_id=${CID}" \
    -d "scope=${scope}" \
    -d "client_secret=${CSEC}" \
    -d "grant_type=client_credentials")
  echo "$code"
}

# ---- Fabric REST API token (api.fabric.microsoft.com) ----
CODE=$(get_token "https://api.fabric.microsoft.com/.default" /tmp/fabric_token.json)
echo "== Fabric token request HTTP: $CODE =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/fabric_token.json'))
if 'access_token' in d:
    print("TOKEN OK — scope/roles:", d.get('scope'))
    open('/tmp/fabric_tok.txt','w').write(d['access_token'])
else:
    print("TOKEN FAILED:", json.dumps(d, indent=2, ensure_ascii=False))
PY
if [ ! -f /tmp/fabric_tok.txt ]; then
  echo "No Fabric token; the app may have no Fabric API permission. Exiting."
  exit 0
fi
Tk=$(cat /tmp/fabric_tok.txt)

# ---- List all workspaces the service principal can see ----
CODE=$(curl -s -o /tmp/fabric_ws.json -w "%{http_code}" \
  -H "Authorization: Bearer ${Tk}" \
  "https://api.fabric.microsoft.com/v1/workspaces")
echo
echo "== GET /v1/workspaces -> HTTP $CODE =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/fabric_ws.json'))
print(json.dumps(d, indent=2, ensure_ascii=False))
PY

# ---- Try to list items inside the target workspace ----
CODE=$(curl -s -o /tmp/fabric_items.json -w "%{http_code}" \
  -H "Authorization: Bearer ${Tk}" \
  "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items")
echo
echo "== GET /v1/workspaces/${WS_ID}/items -> HTTP $CODE =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/fabric_items.json'))
print(json.dumps(d, indent=2, ensure_ascii=False))
PY

# ---- Get the workspace itself ----
CODE=$(curl -s -o /tmp/fabric_ws1.json -w "%{http_code}" \
  -H "Authorization: Bearer ${Tk}" \
  "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}")
echo
echo "== GET /v1/workspaces/${WS_ID} -> HTTP $CODE =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/fabric_ws1.json'))
print(json.dumps(d, indent=2, ensure_ascii=False))
PY
