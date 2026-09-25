"""
title: Fabric Permissions Discovery — Delegated User
author: Haadthip DIO
version: 0.1.0
required_open_webui_version: 0.11.0

Inspects the signed-in user's Fabric SQL permissions using delegated OAuth token.
Returns accessible schemas, tables, and columns based on HAS_PERMS_BY_NAME checks
and sys metadata views. Never falls back to application identity.
"""

import asyncio
import base64
import json
import re
import struct
from typing import Optional

from pydantic import BaseModel, Field


class Tools:
    SQL_AUDIENCES = {
        "https://database.windows.net",
        "https://database.windows.net/",
        "00000002-0000-0000-c000-000000000000",
    }

    class Valves(BaseModel):
        FABRIC_ENDPOINT: str = Field(
            default="ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com",
            description="Fabric Data Warehouse endpoint hostname",
        )
        DEFAULT_DATABASE: str = Field(
            default="LH_OTC_TEST",
            description="Fabric Warehouse/Lakehouse for permission discovery",
        )
        ODBC_DRIVER: str = Field(
            default="ODBC Driver 18 for SQL Server",
            description="Installed Microsoft SQL Server ODBC driver",
        )
        ALLOWED_TENANT_ID: str = Field(
            default="5045d9c3-3b0b-4315-8594-64118bbd7495",
            description="Entra tenant accepted by this QAS-only delegated tool",
        )
        CONNECT_TIMEOUT: int = Field(default=15, description="ODBC connection timeout")

    def __init__(self):
        self.valves = self.Valves()

    @staticmethod
    def _decode_jwt_claims(token: str) -> dict:
        """Decode claims for fail-fast routing checks; Entra/Fabric validates the signature."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("not a JWT")
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
            if not isinstance(claims, dict):
                raise ValueError("JWT payload is not an object")
            return claims
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Open WebUI supplied an invalid delegated OAuth token.") from exc

    def _require_delegated_token(
        self, __oauth_token__: Optional[dict], __user__: Optional[dict]
    ) -> tuple[str, dict]:
        """Require the current Open WebUI OAuth session's delegated Azure SQL token."""
        if not isinstance(__oauth_token__, dict):
            raise RuntimeError(
                "No delegated OAuth token was supplied by Open WebUI. Sign out and sign in "
                "again after the Azure SQL delegated scope is configured."
            )

        token = str(__oauth_token__.get("access_token") or "").strip()
        if not token:
            raise RuntimeError(
                "Open WebUI OAuth session has no delegated OAuth token. Sign out and sign in again."
            )

        claims = self._decode_jwt_claims(token)
        audience = str(claims.get("aud") or "").rstrip("/")
        allowed_audiences = {item.rstrip("/") for item in self.SQL_AUDIENCES}
        if audience not in allowed_audiences:
            raise RuntimeError(
                "Delegated OAuth token has the wrong audience for Fabric SQL. "
                f"Expected database.windows.net; received {audience or 'none'}."
            )

        tenant = str(claims.get("tid") or "")
        if self.valves.ALLOWED_TENANT_ID and tenant.casefold() != self.valves.ALLOWED_TENANT_ID.casefold():
            raise RuntimeError("Delegated OAuth token belongs to an unapproved tenant.")

        oid = str(claims.get("oid") or "")
        email = ""
        if isinstance(__user__, dict):
            email = str(__user__.get("email") or "")

        return token, {"oid": oid, "tenant_id": tenant, "email": email}

    async def get_my_fabric_permissions(
        self,
        __oauth_token__: Optional[dict] = None,
        __user__: Optional[dict] = None,
    ) -> dict:
        """
        Discover what schemas, tables, and columns the signed-in user can SELECT in Fabric SQL.
        
        Returns:
            {
              "user": {"oid": "...", "email": "..."},
              "database": "LH_OTC_TEST",
              "schemas": [
                {
                  "schema": "dv",
                  "tables": [
                    {
                      "table": "mlv_sale_preformance_aggregate",
                      "has_select": true,
                      "columns": ["BillingDate", "Zone", "SumBillNetRevenue"]
                    }
                  ]
                }
              ]
            }
        """
        token, user_info = self._require_delegated_token(__oauth_token__, __user__)

        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError("pyodbc is not installed in this environment.") from exc

        # Build ODBC connection string with delegated token
        token_bytes = token.encode("utf-16-le")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        attrs_before = {1256: token_struct}

        conn_str = (
            f"Driver={{{self.valves.ODBC_DRIVER}}};"
            f"Server={self.valves.FABRIC_ENDPOINT};"
            f"Database={self.valves.DEFAULT_DATABASE};"
            f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout={self.valves.CONNECT_TIMEOUT};"
        )

        conn = None
        try:
            conn = pyodbc.connect(conn_str, attrs_before=attrs_before, timeout=self.valves.CONNECT_TIMEOUT)
            cursor = conn.cursor()

            # Query all schemas/tables/columns and check HAS_PERMS_BY_NAME for SELECT
            sql = """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                c.name AS column_name,
                HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'SELECT') AS has_table_select,
                HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name) + '.' + QUOTENAME(c.name), 'COLUMN', 'SELECT') AS has_column_select
            FROM sys.schemas s
            INNER JOIN sys.tables t ON s.schema_id = t.schema_id
            INNER JOIN sys.columns c ON t.object_id = c.object_id
            WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA')
            ORDER BY s.name, t.name, c.column_id
            """

            cursor.execute(sql)
            rows = cursor.fetchall()

            # Build nested structure
            schema_map = {}
            for row in rows:
                schema_name, table_name, column_name, has_table_select, has_column_select = row

                # Only include if user has SELECT on table OR column
                if not (has_table_select or has_column_select):
                    continue

                if schema_name not in schema_map:
                    schema_map[schema_name] = {"schema": schema_name, "tables": {}}

                if table_name not in schema_map[schema_name]["tables"]:
                    schema_map[schema_name]["tables"][table_name] = {
                        "table": table_name,
                        "has_select": bool(has_table_select),
                        "columns": [],
                    }

                if has_column_select:
                    schema_map[schema_name]["tables"][table_name]["columns"].append(column_name)

            # Convert to list format
            schemas = []
            for schema_data in schema_map.values():
                tables = list(schema_data["tables"].values())
                schemas.append({"schema": schema_data["schema"], "tables": tables})

            return {
                "user": user_info,
                "database": self.valves.DEFAULT_DATABASE,
                "schemas": schemas,
            }

        except pyodbc.Error as exc:
            raise RuntimeError(f"Fabric SQL permission discovery failed: {exc}") from exc
        finally:
            if conn:
                conn.close()
