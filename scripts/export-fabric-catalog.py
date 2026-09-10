#!/usr/bin/env python3
"""Export read-only Fabric catalog metadata for the knowledge graph."""

import json
import os
import struct
from pathlib import Path

import pyodbc
from azure.identity import ClientSecretCredential


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "docker" / ".env.owui"
OUTPUT_FILE = ROOT / "artifacts" / "fabric-catalog.json"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


def setting(name: str, env: dict[str, str], *fallbacks: str) -> str:
    for candidate in (name, *fallbacks):
        if os.getenv(candidate):
            return os.environ[candidate]
        if env.get(candidate):
            return env[candidate]
    return ""


def main() -> None:
    env = read_env_file(ENV_FILE)
    tenant_id = setting("AZURE_TENANT_ID", env, "MICROSOFT_CLIENT_TENANT_ID")
    client_id = setting("AZURE_CLIENT_ID", env, "MICROSOFT_CLIENT_ID")
    client_secret = setting("AZURE_CLIENT_SECRET", env, "MICROSOFT_CLIENT_SECRET")
    endpoint = setting("FABRIC_ENDPOINT", env) or "ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com"
    database = setting("DEFAULT_DATABASE", env) or "LH_OTC_TEST"

    token = ClientSecretCredential(tenant_id, client_id, client_secret).get_token(
        "https://database.windows.net/.default"
    ).token
    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    connection = pyodbc.connect(
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={endpoint},1433;Database={database};Encrypt=yes;TrustServerCertificate=no;",
        attrs_before={1256: token_struct},
        timeout=30,
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA IN ('dv', 'gold', 'dbo')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
        )
        objects = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION,
                   DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA IN ('dv', 'gold', 'dbo')
            ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
            """
        )
        columns = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
    finally:
        connection.close()

    by_object: dict[str, dict] = {}
    for item in objects:
        name = f"{item['TABLE_SCHEMA']}.{item['TABLE_NAME']}"
        by_object[name] = {
            "schema": item["TABLE_SCHEMA"],
            "name": item["TABLE_NAME"],
            "type": item["TABLE_TYPE"],
            "columns": [],
        }
    for column in columns:
        name = f"{column['TABLE_SCHEMA']}.{column['TABLE_NAME']}"
        if name in by_object:
            by_object[name]["columns"].append(column)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps({"database": database, "objects": list(by_object.values())}, indent=2, default=str))
    print(f"Wrote {len(by_object)} objects and {len(columns)} columns to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()