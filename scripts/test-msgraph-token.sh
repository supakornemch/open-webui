#!/usr/bin/env bash
# Test what data the app's client credentials token can access.
# NOTE: reads secrets from EnterpriseChat/.env — never prints them.
set -euo pipefail

ENV_FILE="/Users/supakorn.emch/Workspace/Haadthip/EnterpriseChat/.env"
# shellcheck disable=SC1090
source "$ENV_FILE"

TENANT="$MICROSOFT_CLIENT_TENANT_ID"
CID="$MICROSOFT_CLIENT_ID"
CSEC="$MICROSOFT_CLIENT_SECRET"

# 1. Get app-only token for Microsoft Graph
RESP=$(curl -s -o /tmp/token.json -w "%{http_code}" \
  -X POST "https://login.microsoftonline.com/${TENANT}/oauth2/v2.0/token" \
  -d "client_id=${CID}" \
  -d "scope=https://graph.microsoft.com/.default" \
  -d "client_secret=${CSEC}" \
  -d "grant_type=client_credentials")

echo "== Token request HTTP status: ${RESP} =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/token.json'))
if 'access_token' in d:
    print("TOKEN OK — scopes (roles) granted:", d.get('scope'))
    open('/tmp/tok.txt','w').write(d['access_token'])
else:
    print("TOKEN FAILED:", json.dumps(d, indent=2))
    exit(1)
PY
if [ ! -f /tmp/tok.txt ]; then exit 1; fi
Tk=$(cat /tmp/tok.txt)

# 2. Try to read another user's profile
CODE=$(curl -s -o /tmp/user.json -w "%{http_code}" \
  -H "Authorization: Bearer ${Tk}" \
  "https://graph.microsoft.com/v1.0/users/supakorn.em@haadthip.com")
echo
echo "== GET /users/supakorn.em@haadthip.com -> HTTP $CODE =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/user.json'))
print(json.dumps(d, indent=2, ensure_ascii=False))
PY

# 3. List users (directory enumeration)
CODE=$(curl -s -o /tmp/users.json -w "%{http_code}" \
  -H "Authorization: Bearer ${Tk}" \
  "https://graph.microsoft.com/v1.0/users?\$top=5&\$select=displayName,userPrincipalName")
echo
echo "== GET /users (list) -> HTTP $CODE =="
python3 - <<'PY'
import json
d = json.load(open('/tmp/users.json'))
print(json.dumps(d, indent=2, ensure_ascii=False))
PY

# 4. What does the app identity itself look like / what roles does it have?
CODE=$(curl -s -o /tmp/sp.json -w "%{http_code}" \
  -H "Authorization: Bearer ${Tk}" \
  "https://graph.microsoft.com/v1.0/servicePrincipals(appId='${CID}')?\$select=displayName,appId")
echo
echo "== GET /servicePrincipals(appId=ours) -> HTTP $CODE =="
cat /tmp/sp.json; echo
