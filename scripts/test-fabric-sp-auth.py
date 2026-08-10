#!/usr/bin/env python3
"""
Test Fabric Data Warehouse connection using Service Principal (App ID + Secret).

Reads AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID from
docker/.env.owui or the current environment.
"""

import os
import struct
import sys

# ── Determine env file location ──────────────────────────────────────────
ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docker",
    ".env.owui",
)

def load_dotenv(path: str) -> dict:
    """Simple .env parser — no dependency on python-dotenv."""
    result = {}
    if not os.path.exists(path):
        print(f"⚠️  {path} not found, relying on os.environ only.")
        return result
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            result[key] = value
    return result

# Load env vars (os.environ wins over .env file)
env = load_dotenv(ENV_FILE)

TENANT_ID = os.environ.get("AZURE_TENANT_ID") or env.get("AZURE_TENANT_ID") or os.environ.get("MICROSOFT_CLIENT_TENANT_ID") or env.get("MICROSOFT_CLIENT_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID") or env.get("AZURE_CLIENT_ID") or os.environ.get("MICROSOFT_CLIENT_ID") or env.get("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET") or env.get("AZURE_CLIENT_SECRET") or os.environ.get("MICROSOFT_CLIENT_SECRET") or env.get("MICROSOFT_CLIENT_SECRET", "")
FABRIC_ENDPOINT = os.environ.get("FABRIC_ENDPOINT") or env.get("FABRIC_ENDPOINT", "ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com")
DATABASE = os.environ.get("DEFAULT_DATABASE") or env.get("DEFAULT_DATABASE", "LH_OTC_TEST")
ODBC_DRIVER = os.environ.get("ODBC_DRIVER") or env.get("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

print("=" * 60)
print("🔐 Fabric Service Principal Auth Test")
print("=" * 60)
print(f"Tenant ID : {TENANT_ID[:20]}...{'✅' if TENANT_ID else '❌ MISSING'}")
print(f"Client ID : {CLIENT_ID[:20]}...{'✅' if CLIENT_ID else '❌ MISSING'}")
print(f"Secret    : {'✅ SET' if CLIENT_SECRET else '❌ MISSING'} ({len(CLIENT_SECRET)} chars)")
print(f"Endpoint  : {FABRIC_ENDPOINT}")
print(f"Database  : {DATABASE}")
print(f"ODBC      : {ODBC_DRIVER}")
print()

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    print("❌ Missing required credentials. Aborting.")
    sys.exit(1)

# ── Step 1: Acquire token via ClientSecretCredential ──────────────────────
print("Step 1: Acquiring Entra ID token via ClientSecretCredential ...")
try:
    from azure.identity import ClientSecretCredential

    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    token = credential.get_token("https://database.windows.net/.default")
    print(f"✅ Token acquired! Expires: {token.expires_on}")

except Exception as e:
    print(f"❌ Failed to acquire token: {e}")
    sys.exit(1)

# ── Step 2: Connect to Fabric via pyodbc with token ───────────────────────
print("\nStep 2: Connecting to Fabric Data Warehouse ...")
token_bytes = token.token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
SQL_COPT_SS_ACCESS_TOKEN = 1256

conn_str = (
    f"Driver={{{ODBC_DRIVER}}};"
    f"Server={FABRIC_ENDPOINT},1433;"
    f"Database={DATABASE};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)

try:
    import pyodbc

    conn = pyodbc.connect(
        conn_str,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        timeout=15,
    )
    print("✅ Connected!")

    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION AS sql_version, DB_NAME() AS current_db")
    row = cursor.fetchone()
    print(f"   SQL Version: {row.sql_version[:80]}...")
    print(f"   Database   : {row.current_db}")

    # ── Step 3: Run a simple query ────────────────────────────────────────
    print("\nStep 3: Running test query ...")
    cursor.execute("""
        SELECT TOP 3 TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'VIEW'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)
    rows = cursor.fetchall()
    if rows:
        print("✅ Query successful! Sample views:")
        for r in rows:
            print(f"   {r.TABLE_SCHEMA}.{r.TABLE_NAME}")
    else:
        print("⚠️  Query returned no rows (but connection works).")

    conn.close()
    print("\n" + "=" * 60)
    print("✅ SUCCESS: Service Principal auth to Fabric works!")
    print("=" * 60)

except Exception as e:
    print(f"❌ Connection/query failed: {e}")
    print("\n💡 Possible causes:")
    print("   1. Service principal not added to Fabric workspace")
    print("   2. Service principal lacks read permission on the warehouse")
    print("   3. Network/VNet blocks outbound to Fabric endpoint")
    print("   4. IP firewall on Fabric SQL endpoint")
    sys.exit(1)
