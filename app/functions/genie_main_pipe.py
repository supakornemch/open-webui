"""
title: Genie AI — Main Assistant
author: Haadthip DIO
version: 1.0.0
required_open_webui_version: 0.11.0
"""
import asyncio
import base64
import json
import os
import re
import struct
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field


FABRIC_TOOL = {
    "type": "function",
    "function": {
        "name": "query_fabric",
        "description": (
            "Execute read-only SQL query against Microsoft Fabric Data Warehouse "
            "using the signed-in user's delegated token. Use this for sales data, "
            "customer info, credit/AR, targets, quantitative business questions, "
            "or when asked 'what data can I access' / 'ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": (
                        "T-SQL SELECT or WITH query. Must use explicit column names (no SELECT *), "
                        "schema-qualified table names (e.g., dbo.dim_customer), and read-only operations only. "
                        "To discover accessible tables: SELECT TOP 10 table_schema, table_name FROM INFORMATION_SCHEMA.TABLES WHERE table_schema NOT IN ('sys','INFORMATION_SCHEMA')"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 20,
                    "description": "Maximum rows to return (max 20)",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Row offset for pagination",
                },
            },
            "required": ["sql_query"],
        },
    },
}


class Pipe:
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
            default="",
            description="Fabric Data Warehouse endpoint hostname",
        )
        DEFAULT_DATABASE: str = Field(
            default="LH_OTC_TEST",
            description="Fabric Warehouse/Lakehouse database name",
        )
        ODBC_DRIVER: str = Field(
            default="ODBC Driver 18 for SQL Server",
            description="Installed Microsoft SQL Server ODBC driver",
        )
        ALLOWED_TENANT_ID: str = Field(
            default="",
            description="Entra tenant ID restriction (leave empty to allow any)",
        )
        LLM_BASE_URL: str = Field(default="", description="LiteLLM base URL")
        LLM_API_KEY: str = Field(default="", description="LiteLLM API key")
        LLM_MODEL: str = Field(
            default="genie.deploy-gpt-5.6-luna",
            description="Model ID for orchestration",
        )
        MAX_TOOL_ROUNDS: int = Field(default=8, description="Max tool loop iterations")
        DEFAULT_LIMIT: int = Field(default=20, description="Default row limit")
        CONNECT_TIMEOUT: int = Field(default=15, description="ODBC connection timeout")

    def __init__(self):
        self.valves = self.Valves()
        v = self.valves
        if not v.FABRIC_ENDPOINT:
            v.FABRIC_ENDPOINT = os.getenv(
                "FABRIC_ENDPOINT",
                "ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com",
            )
        if not v.ALLOWED_TENANT_ID:
            v.ALLOWED_TENANT_ID = os.getenv("ALLOWED_TENANT_ID", "5045d9c3-3b0b-4315-8594-64118bbd7495")
        if not v.LLM_BASE_URL:
            base = os.getenv("OPENAI_API_BASE_URL", "").rstrip("/")
            v.LLM_BASE_URL = base[:-3] if base.endswith("/v1") else base
        if not v.LLM_API_KEY:
            v.LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")

    @staticmethod
    def _decode_jwt_claims(token: str) -> dict:
        """Decode JWT claims (Entra validates signature)."""
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
            raise RuntimeError("Invalid delegated OAuth token.") from exc

    def _require_delegated_token(
        self, __oauth_token__: Optional[dict], __user__: Optional[dict]
    ) -> tuple[str, dict]:
        """Require delegated Azure SQL token from Open WebUI OAuth session."""
        if not isinstance(__oauth_token__, dict):
            raise RuntimeError(
                "No delegated OAuth token. Sign out and sign in again with Azure SQL scope configured."
            )

        token = str(__oauth_token__.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("OAuth session has no delegated token. Sign out and sign in again.")

        claims = self._decode_jwt_claims(token)
        audience = str(claims.get("aud") or "").rstrip("/")
        allowed_audiences = {item.rstrip("/") for item in self.SQL_AUDIENCES}
        if audience not in allowed_audiences:
            raise RuntimeError(
                f"Token audience {audience or 'none'} is not database.windows.net; wrong scope configured."
            )

        tenant = str(claims.get("tid") or "")
        if self.valves.ALLOWED_TENANT_ID and tenant.casefold() != self.valves.ALLOWED_TENANT_ID.casefold():
            raise RuntimeError("Token belongs to an unapproved tenant.")

        scopes = {scope.casefold() for scope in str(claims.get("scp") or "").split()}
        if "user_impersonation" not in scopes:
            raise RuntimeError("Token missing user_impersonation scope; app-only tokens rejected.")

        oid = str(claims.get("oid") or "").strip()
        if not oid:
            raise RuntimeError("Token missing user oid claim.")

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
            return "Error: Only read-only SELECT or WITH queries allowed."
        if re.search(
            r"\b(?:INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|DENY|EXEC|EXECUTE)\b",
            query,
            re.IGNORECASE,
        ):
            return "Error: Data-modifying statements not allowed."
        if cls.WILDCARD_SELECT_RE.search(query):
            return "Error: SELECT * not allowed; list explicit columns only."
        return None

    @staticmethod
    def _extract_table_names(sql: str) -> set[str]:
        """Extract table names from SQL (simple regex parser)."""
        sql_no_comments = re.sub(r"--[^\n]*", "", sql)
        sql_no_comments = re.sub(r"/\*.*?\*/", "", sql_no_comments, flags=re.DOTALL)
        table_pattern = re.compile(
            r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)?)",
            re.IGNORECASE,
        )
        matches = table_pattern.findall(sql_no_comments)
        return {match.lower().strip() for match in matches if match.strip()}

    @classmethod
    def _validate_table_access(cls, sql_query: str, allowed_tables: set[str]) -> Optional[str]:
        """Reject queries accessing tables outside allowlist."""
        referenced_tables = cls._extract_table_names(sql_query)
        if not referenced_tables:
            return "Error: Query must reference at least one schema-qualified table."

        # System metadata schemas are always allowed (users have implicit access)
        SYSTEM_SCHEMAS = {"information_schema", "sys"}
        data_tables = referenced_tables - {t for t in referenced_tables if any(t.startswith(s + ".") for s in SYSTEM_SCHEMAS)}
        unauthorized = data_tables - allowed_tables
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
                f"Unsupported database `{candidate}`; only `{self.valves.DEFAULT_DATABASE}` allowed."
            )
        return self.valves.DEFAULT_DATABASE

    def _discover_allowed_tables(self, cursor) -> set[str]:
        """Return only SELECT-able tables for current delegated user."""
        cursor.execute(
            """
            SELECT s.name, t.name
            FROM sys.schemas AS s
            INNER JOIN sys.tables AS t ON t.schema_id = s.schema_id
            WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA')
              AND HAS_PERMS_BY_NAME(
                  QUOTENAME(s.name) + '.' + QUOTENAME(t.name),
                  'OBJECT',
                  'SELECT'
              ) = 1
            """
        )
        return {f"{schema}.{table}".casefold() for schema, table in cursor.fetchall()}

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
                "pyodbc and Microsoft ODBC Driver 18 must be installed."
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
            allowed_tables = self._discover_allowed_tables(cursor)
            access_error = self._validate_table_access(cleaned_query, allowed_tables)
            if access_error:
                return access_error

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

    async def _execute_fabric_query(
        self,
        sql_query: str,
        limit: int,
        offset: int,
        __oauth_token__: Optional[dict],
        __user__: Optional[dict],
    ) -> str:
        """Execute Fabric query with delegated token."""
        cleaned_query = (sql_query or "").strip()
        validation_error = self._validate_read_only_query(cleaned_query)
        if validation_error:
            return validation_error

        try:
            access_token, identity = self._require_delegated_token(__oauth_token__, __user__)
            target_db = self.valves.DEFAULT_DATABASE
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

    def _dispatch_tool(
        self,
        name: str,
        args: dict,
        oauth_token: dict,
        user: dict,
    ) -> str:
        """Dispatch tool call (sync wrapper)."""
        if name == "query_fabric":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self._execute_fabric_query(
                        sql_query=args.get("sql_query", ""),
                        limit=args.get("limit", 20),
                        offset=args.get("offset", 0),
                        __oauth_token__=oauth_token,
                        __user__=user,
                    )
                )
            finally:
                loop.close()
        return json.dumps({"success": False, "error": f"unknown tool: {name}"})

    def pipe(self, body: dict, __user__: dict = None, __oauth_token__: dict = None, __event_emitter__=None) -> str:
        """Main Pipe entry point — orchestrates tool loop with delegated token."""
        messages = list(body.get("messages") or [])
        system = body.get("system")
        if system:
            messages.insert(0, {"role": "system", "content": system})

        client = OpenAI(
            api_key=self.valves.LLM_API_KEY,
            base_url=self.valves.LLM_BASE_URL.rstrip("/") + "/v1",
        )

        for _ in range(max(1, min(self.valves.MAX_TOOL_ROUNDS, 10))):
            response = client.chat.completions.create(
                model=self.valves.LLM_MODEL,
                messages=messages,
                tools=[FABRIC_TOOL],  # type: ignore
                tool_choice="auto",
                extra_body={"prompt_cache_key": "genie-qas"},
            )
            choice = response.choices[0]
            msg = choice.message
            if choice.finish_reason != "tool_calls" or not msg.tool_calls:
                return msg.content or ""

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [x.model_dump() for x in msg.tool_calls],
                }
            )
            for call in msg.tool_calls:
                func = getattr(call, "function", None)
                if not func:
                    continue
                args = json.loads(func.arguments or "{}")
                result = self._dispatch_tool(func.name, args, __oauth_token__ or {}, __user__ or {})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        return "ขออภัยครับ ระบบใช้เวลานานเกินกำหนด กรุณาลองใหม่อีกครั้ง"
