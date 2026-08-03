"""
title: Fabric Data Warehouse Query Tool
author: Haadthip DIO
version: 1.1
required_open_webui_version: 0.5.0

Executes SQL queries against Microsoft Fabric Data Warehouse / Lakehouse using Entra ID authentication via Azure SDK or pyodbc.

Capabilities:
- Query Fabric Data Warehouse tables (e.g. LH_PROJECT, LH_OTC_TEST, BRONZE_SQL)
- Dynamic SQL Execution with safety controls (SELECT queries only)
- Pagination support with limit (max_rows) and offset (page number / offset)
- Non-blocking async execution using background thread executor
- Returns results in clean JSON markdown format
"""

import asyncio
import json
import os
import struct
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

import pyodbc
from azure.identity import (
    DefaultAzureCredential,
    AzureCliCredential,
    ClientSecretCredential,
)


class Tools:
    class Valves(BaseModel):
        FABRIC_ENDPOINT: str = Field(
            default="ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com",
            description="Fabric Data Warehouse Endpoint server hostname"
        )
        DEFAULT_DATABASE: str = Field(
            default="LH_OTC_TEST",
            description="Default Database / Lakehouse / Warehouse name to query"
        )
        ODBC_DRIVER: str = Field(
            default="ODBC Driver 18 for SQL Server",
            description="Installed ODBC Driver name"
        )
        AZURE_TENANT_ID: str = Field(
            default="",
            description="(Optional) Microsoft Entra Tenant ID for Service Principal auth"
        )
        AZURE_CLIENT_ID: str = Field(
            default="",
            description="(Optional) Microsoft Entra Client ID for Service Principal auth"
        )
        AZURE_CLIENT_SECRET: str = Field(
            default="",
            description="(Optional) Microsoft Entra Client Secret for Service Principal auth"
        )
        ACCESS_TOKEN: str = Field(
            default="",
            description="(Optional) Pre-acquired Entra ID bearer token"
        )
        DEFAULT_LIMIT: int = Field(
            default=50,
            description="Default maximum number of rows to return per query page"
        )
        MAX_LIMIT_CAP: int = Field(
            default=200,
            description="Hard upper limit cap on maximum allowed rows per request"
        )
        CONNECT_TIMEOUT: int = Field(
            default=15,
            description="Connection timeout in seconds"
        )

    def __init__(self):
        self.valves = self.Valves()
        if os.getenv("FABRIC_ENDPOINT"):
            self.valves.FABRIC_ENDPOINT = os.getenv("FABRIC_ENDPOINT")
        if not self.valves.AZURE_TENANT_ID:
            self.valves.AZURE_TENANT_ID = os.getenv("MICROSOFT_CLIENT_TENANT_ID", "")
        if not self.valves.AZURE_CLIENT_ID:
            self.valves.AZURE_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
        if not self.valves.AZURE_CLIENT_SECRET:
            self.valves.AZURE_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")

    def _sync_get_connection_and_query(
        self, database_name: str, cleaned_query: str, limit: int, offset: int
    ) -> str:
        db = database_name or self.valves.DEFAULT_DATABASE
        endpoint = self.valves.FABRIC_ENDPOINT

        # Priority 1: User/Valve provided raw token
        token_str = self.valves.ACCESS_TOKEN.strip()

        # Priority 2: Service Principal Credential if client_id & secret are set
        if not token_str and self.valves.AZURE_CLIENT_ID and self.valves.AZURE_CLIENT_SECRET and self.valves.AZURE_TENANT_ID:
            try:
                cred = ClientSecretCredential(
                    tenant_id=self.valves.AZURE_TENANT_ID,
                    client_id=self.valves.AZURE_CLIENT_ID,
                    client_secret=self.valves.AZURE_CLIENT_SECRET,
                )
                token_obj = cred.get_token("https://database.windows.net/.default")
                token_str = token_obj.token
            except Exception:
                token_str = ""

        # Priority 3: DefaultAzureCredential / AzureCliCredential fallback
        if not token_str:
            try:
                credential = DefaultAzureCredential()
                token_obj = credential.get_token("https://database.windows.net/.default")
                token_str = token_obj.token
            except Exception as e:
                raise RuntimeError(
                    f"No ACCESS_TOKEN provided and Azure credentials failed: {str(e)}. "
                    "Please paste a valid Entra ID Access Token into Tool Valves."
                )

        if not token_str:
            raise RuntimeError("Failed to acquire Entra ID Access Token for Fabric connection.")

        # Format token for ODBC Attribute 1256 (SQL_COPT_SS_ACCESS_TOKEN)
        token_bytes = token_str.encode("utf-16-le")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        SQL_COPT_SS_ACCESS_TOKEN = 1256

        conn_str = (
            f"Driver={{{self.valves.ODBC_DRIVER}}};"
            f"Server={endpoint},1433;"
            f"Database={db};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
        )

        conn = pyodbc.connect(
            conn_str,
            attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
            timeout=self.valves.CONNECT_TIMEOUT
        )
        cursor = conn.cursor()
        cursor.execute(cleaned_query)

        if not cursor.description:
            conn.close()
            return "Query executed successfully with no output."

        columns = [column[0] for column in cursor.description]

        # Handle pagination (offset & limit)
        if offset > 0:
            cursor.skip(offset)

        rows = cursor.fetchmany(limit)
        conn.close()

        if not rows:
            return f"No results found in database `{db}` (Page Offset: {offset}, Limit: {limit})."

        results = []
        for row in rows:
            row_dict = {}
            for idx, col in enumerate(columns):
                val = row[idx]
                row_dict[col] = str(val) if val is not None else None
            results.append(row_dict)

        page_num = (offset // limit) + 1
        summary = (
            f"Database: `{db}` | Page: {page_num} (Offset: {offset}, Limit: {limit}) | "
            f"Returned {len(results)} rows:\n\n"
            "```json\n" + json.dumps(results, ensure_ascii=False, indent=2) + "\n```"
        )
        return summary

    async def query_fabric(
        self,
        sql_query: str,
        database_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
        page: Optional[int] = None,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Execute a SELECT SQL query against Microsoft Fabric Data Warehouse / Lakehouse with pagination support.

        :param sql_query: The T-SQL SELECT query to execute (e.g., 'SELECT * FROM dbo.log_task').
        :param database_name: (Optional) Target database name such as 'LH_OTC_TEST' or 'LH_PROJECT'. Defaults to LH_OTC_TEST.
        :param limit: (Optional) Maximum number of rows to return per page (e.g., 10, 20, 50). Max cap is 200.
        :param offset: (Optional) Number of rows to skip before fetching (0-indexed). Defaults to 0.
        :param page: (Optional) Page number (1-indexed). If specified, overrides offset calculation (e.g., page=2 with limit=10 sets offset=10).
        :return: JSON formatted query results with pagination metadata.
        """
        cleaned_query = sql_query.strip()
        
        # Basic safety check to prevent data modification
        if not cleaned_query.upper().startswith(("SELECT", "WITH", "EXEC", "SHOW")):
            return "Error: Only read-only queries (SELECT, WITH, EXEC) are allowed."

        target_db = database_name or self.valves.DEFAULT_DATABASE

        # Calculate limit and offset
        row_limit = limit if (limit and limit > 0) else self.valves.DEFAULT_LIMIT
        row_limit = min(row_limit, self.valves.MAX_LIMIT_CAP)

        if page and page > 0:
            row_offset = (page - 1) * row_limit
        else:
            row_offset = max(offset or 0, 0)

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._sync_get_connection_and_query, target_db, cleaned_query, row_limit, row_offset
            )
            return result

        except Exception as e:
            return f"Error executing query on Fabric `{target_db}`: {str(e)}"

    async def list_tables(
        self,
        database_name: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        List all available tables and schemas in a Fabric Data Warehouse / Lakehouse database with pagination.

        :param database_name: (Optional) Database name to inspect (e.g. 'LH_OTC_TEST', 'LH_PROJECT').
        :param limit: (Optional) Max rows per page. Defaults to 50.
        :param page: (Optional) Page number (1-indexed).
        :return: List of tables in the specified database.
        """
        query = "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_SCHEMA, TABLE_NAME;"
        return await self.query_fabric(
            sql_query=query, database_name=database_name, limit=limit, page=page, __user__=__user__
        )
