"""
title: Fabric Query — Delegated User Token (QAS Experiment)
author: Haadthip DIO
version: 0.1.0
required_open_webui_version: 0.11.0

QAS-only clone used to prove Microsoft Fabric SQL tool calls with the signed-in
user's Microsoft OAuth access token. It fails closed and never falls back to an
application identity, managed identity, or static token.
"""

import asyncio
import base64
import json
import re
import struct
from typing import Optional

from pydantic import BaseModel, Field


class Tools:
    HARD_MAX_LIMIT = 20
    SQL_AUDIENCES = {
        "https://database.windows.net",
        "https://database.windows.net/",
        "00000002-0000-0000-c000-000000000000",
    }
    WILDCARD_SELECT_RE = re.compile(
        r"(?:\bSELECT\b|,)\s*(?:DISTINCT\s+)?(?:TOP\s+\d+\s+)?"
        r"(?:[A-Za-z_]\w*[.])?\s*\*(?=\s*(?:,|\bFROM\b|$))",
        re.IGNORECASE,
    )

    class Valves(BaseModel):
        FABRIC_ENDPOINT: str = Field(
            default="ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com",
            description="Fabric Data Warehouse endpoint hostname",
        )
        DEFAULT_DATABASE: str = Field(
            default="LH_OTC_TEST",
            description="Only Fabric Warehouse/Lakehouse allowed for this QAS experiment",
        )
        ODBC_DRIVER: str = Field(
            default="ODBC Driver 18 for SQL Server",
            description="Installed Microsoft SQL Server ODBC driver",
        )
        ALLOWED_TENANT_ID: str = Field(
            default="5045d9c3-3b0b-4315-8594-64118bbd7495",
            description="Entra tenant accepted by this QAS-only delegated tool",
        )
        DEFAULT_LIMIT: int = Field(default=20, description="Default row limit")
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

        scopes = {scope.casefold() for scope in str(claims.get("scp") or "").split()}
        if "user_impersonation" not in scopes:
            raise RuntimeError(
                "OAuth token does not contain the delegated scope user_impersonation; "
                "app-only tokens and role claims are rejected."
            )

        oid = str(claims.get("oid") or "").strip()
        if not oid:
            raise RuntimeError("Delegated OAuth token does not contain an immutable user oid claim.")

        username = str(
            claims.get("preferred_username")
            or claims.get("upn")
            or ((__user__ or {}).get("email"))
            or "unknown-user"
        )
        return token, {"oid": oid, "tid": tenant, "username": username}

    @classmethod
    def _validate_read_only_query(cls, query: str) -> Optional[str]:
        if not query:
            return "Error: SQL query cannot be empty."
        if not query.upper().startswith(("SELECT", "WITH")):
            return "Error: Only read-only SELECT or WITH queries are allowed."
        if re.search(
            r"\b(?:INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|DENY|EXEC|EXECUTE)\b",
            query,
            re.IGNORECASE,
        ):
            return "Error: Data-modifying and procedure statements are not allowed."
        if cls.WILDCARD_SELECT_RE.search(query):
            return "Error: SELECT * is not allowed; list only the required columns."
        return None

    @staticmethod
    def _extract_table_names(sql: str) -> set[str]:
        """
        Extract table names from SQL query (simple regex-based parser).
        Returns normalized set like {'schema.table', 'table'}.
        """
        # Remove comments
        sql_no_comments = re.sub(r"--[^\n]*", "", sql)
        sql_no_comments = re.sub(r"/\*.*?\*/", "", sql_no_comments, flags=re.DOTALL)
        
        # Find FROM and JOIN clauses
        table_pattern = re.compile(
            r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)?)",
            re.IGNORECASE
        )
        matches = table_pattern.findall(sql_no_comments)
        return {match.lower().strip() for match in matches if match.strip()}

    @classmethod
    def _validate_table_access(cls, sql_query: str, allowed_tables: Optional[list[str]]) -> Optional[str]:
        """
        Check whether the SQL query references only allowed tables.
        Returns error message if unauthorized, None if OK.
        """
        if allowed_tables is None:
            return None  # Skip guardrail if not provided (backward compat)
        
        referenced_tables = cls._extract_table_names(sql_query)
        allowed_set = {table.lower().strip() for table in allowed_tables}
        
        unauthorized = referenced_tables - allowed_set
        if unauthorized:
            return (
                f"Error: ไม่มีสิทธิ์เข้าถึงตาราง {', '.join(sorted(unauthorized))}. "
                "กรุณาติดต่อผู้ดูแลระบบหรือเจ้าของข้อมูล"
            )
        return None

    def _normalise_limit(self, requested_limit: Optional[int]) -> int:
        try:
            value = int(requested_limit) if requested_limit is not None else int(self.valves.DEFAULT_LIMIT)
        except (TypeError, ValueError):
            value = self.HARD_MAX_LIMIT
        return max(1, min(value, self.HARD_MAX_LIMIT))

    def _resolve_database_name(self, database_name: Optional[str]) -> str:
        candidate = (database_name or self.valves.DEFAULT_DATABASE).strip()
        if candidate.casefold() != self.valves.DEFAULT_DATABASE.casefold():
            raise ValueError(
                f"Unsupported Fabric database `{candidate}`; only `{self.valves.DEFAULT_DATABASE}` is allowed."
            )
        return self.valves.DEFAULT_DATABASE

    def _sync_get_connection_and_query(
        self,
        database_name: str,
        cleaned_query: str,
        limit: int,
        offset: int,
        access_token: str,
    ) -> str:
        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError(
                "pyodbc and Microsoft ODBC Driver 18 must be installed in the Open WebUI image."
            ) from exc

        db = self._resolve_database_name(database_name)
        token_bytes = access_token.encode("utf-16-le")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        conn_str = (
            f"Driver={{{self.valves.ODBC_DRIVER}}};"
            f"Server={self.valves.FABRIC_ENDPOINT},1433;"
            f"Database={db};Encrypt=yes;TrustServerCertificate=no;"
        )

        connection = None
        try:
            connection = pyodbc.connect(
                conn_str,
                attrs_before={1256: token_struct},
                timeout=self.valves.CONNECT_TIMEOUT,
            )
            cursor = connection.cursor()
            cursor.execute(cleaned_query)
            if not cursor.description:
                return "Query executed successfully with no output."
            columns = [column[0] for column in cursor.description]
            remaining = max(offset, 0)
            while remaining:
                skipped = cursor.fetchmany(min(remaining, self.HARD_MAX_LIMIT))
                if not skipped:
                    break
                remaining -= len(skipped)
            rows = cursor.fetchmany(limit)
        finally:
            if connection is not None:
                connection.close()

        results = [
            {column: (str(row[index]) if row[index] is not None else None) for index, column in enumerate(columns)}
            for row in rows
        ]
        return (
            f"Database: `{db}` | Offset: {offset} | Limit: {limit} | Returned {len(results)} rows:\n\n"
            "```json\n" + json.dumps(results, ensure_ascii=False, indent=2) + "\n```"
        )

    async def query_fabric_delegated(
        self,
        sql_query: str,
        database_name: Optional[str] = None,
        limit: Optional[int] = 20,
        offset: Optional[int] = 0,
        allowed_tables: Optional[list[str]] = None,
        __oauth_token__: Optional[dict] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        QAS experiment: execute a read-only Fabric SQL query as the signed-in user.
        Requires Open WebUI's server-side Microsoft OAuth session token and never
        falls back to a Service Principal. Use explicit columns; maximum 20 rows.
        
        Args:
            sql_query: T-SQL SELECT query
            database_name: Target Fabric database (defaults to LH_OTC_TEST)
            limit: Maximum rows to return (max 20)
            offset: Row offset for pagination
            allowed_tables: Optional allowlist of schema.table names user can SELECT.
                           If provided, tool will reject queries referencing tables
                           not in this list. Pass output from get_my_fabric_permissions.
            __oauth_token__: Open WebUI OAuth session (auto-injected)
            __user__: Open WebUI user context (auto-injected)
        """
        cleaned_query = (sql_query or "").strip()
        validation_error = self._validate_read_only_query(cleaned_query)
        if validation_error:
            return validation_error

        # Check table access if allowed_tables is provided
        access_error = self._validate_table_access(cleaned_query, allowed_tables)
        if access_error:
            return access_error

        try:
            access_token, identity = self._require_delegated_token(__oauth_token__, __user__)
            target_db = self._resolve_database_name(database_name)
            row_limit = self._normalise_limit(limit)
            row_offset = max(int(offset or 0), 0)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_get_connection_and_query,
                target_db,
                cleaned_query,
                row_limit,
                row_offset,
                access_token,
            )
            return f"Delegated user {identity['username']} (oid: {identity['oid']})\n\n{result}"
        except Exception as exc:
            return f"Delegated Fabric query denied: {exc}"
