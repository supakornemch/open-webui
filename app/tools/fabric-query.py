"""
title: Fabric Data Warehouse Query Tool
author: Haadthip DIO
version: 1.4
required_open_webui_version: 0.5.0

Query Microsoft Fabric Data Warehouse (LH_OTC_TEST) using Entra ID auth.
Domain helpers: Sales/OTC, Targets, Customers, Products, Credit, Coolers, Visits, RFM Segmentation.
Custom T-SQL (SELECT/WITH only), schema inspection, pagination (hard cap: 20).
"""

import asyncio
import json
import os
import re
import struct
from typing import Optional
from pydantic import BaseModel, Field

import pyodbc
from azure.identity import (
    DefaultAzureCredential,
    ClientSecretCredential,
)


class Tools:
    HARD_MAX_LIMIT = 20
    WILDCARD_SELECT_RE = re.compile(
        r"(?:\bSELECT\b|,)\s*"
        r"(?:DISTINCT\s+)?(?:TOP\s+\d+\s+)?"
        r"(?:[A-Za-z_]\w*[.])?\s*\*"
        r"(?=\s*(?:,|\bFROM\b|$))",
        re.IGNORECASE,
    )

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
            default=20,
            description="Default maximum number of rows to return per query page (hard cap: 20)"
        )
        MAX_LIMIT_CAP: int = Field(
            default=20,
            description="Maximum rows per request; the tool hard-caps this value at 20"
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

    @classmethod
    def _validate_read_only_query(cls, query: str) -> Optional[str]:
        if not query:
            return "Error: SQL query cannot be empty."

        upper_query = query.upper()
        if not upper_query.startswith(("SELECT", "WITH")):
            return "Error: Only read-only queries (SELECT or WITH) are allowed."

        if re.search(
            r"\b(?:INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|DENY|EXEC|EXECUTE)\b",
            query,
            re.IGNORECASE,
        ):
            return "Error: Data-modifying and procedure statements are not allowed."

        if cls.WILDCARD_SELECT_RE.search(query):
            return (
                "Error: SELECT * is not allowed. "
                "Select only the columns required to answer the question."
            )

        return None

    def _normalise_limit(self, requested_limit: Optional[int]) -> int:
        try:
            default_limit = int(self.valves.DEFAULT_LIMIT)
        except (TypeError, ValueError):
            default_limit = self.HARD_MAX_LIMIT

        try:
            configured_cap = int(self.valves.MAX_LIMIT_CAP)
        except (TypeError, ValueError):
            configured_cap = self.HARD_MAX_LIMIT

        try:
            row_limit = int(requested_limit) if requested_limit is not None else default_limit
        except (TypeError, ValueError):
            row_limit = default_limit

        if row_limit <= 0:
            row_limit = default_limit
        if row_limit <= 0:
            row_limit = self.HARD_MAX_LIMIT

        if configured_cap <= 0:
            configured_cap = self.HARD_MAX_LIMIT

        return max(1, min(row_limit, configured_cap, self.HARD_MAX_LIMIT))

    @staticmethod
    def _sql_literal(value: object) -> str:
        """Quote a user-supplied string for a read-only SQL filter."""
        return "'" + str(value).replace("'", "''") + "'"

    def _sync_get_connection_and_query(
        self, database_name: str, cleaned_query: str, limit: int, offset: int
    ) -> str:
        db = database_name or self.valves.DEFAULT_DATABASE
        endpoint = self.valves.FABRIC_ENDPOINT

        token_str = self.valves.ACCESS_TOKEN.strip()
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

        # Priority 3: DefaultAzureCredential fallback
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

        conn = None
        try:
            conn = pyodbc.connect(
                conn_str,
                attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
                timeout=self.valves.CONNECT_TIMEOUT
            )
            cursor = conn.cursor()
            cursor.execute(cleaned_query)

            if not cursor.description:
                return "Query executed successfully with no output."

            columns = [column[0] for column in cursor.description]

            remaining_offset = max(offset, 0)
            while remaining_offset > 0:
                skipped_rows = cursor.fetchmany(min(remaining_offset, self.HARD_MAX_LIMIT))
                if not skipped_rows:
                    break
                remaining_offset -= len(skipped_rows)

            rows = cursor.fetchmany(limit)
        finally:
            if conn is not None:
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
        Execute T-SQL SELECT/WITH query. Must list explicit columns (no SELECT *).
        :param sql_query: T-SQL with explicit columns, e.g. 'SELECT TOP 20 BillingDate, SumBillNetRevenue FROM dv.mlv_sale_preformance_aggregate'
        :param limit: Max rows (hard cap: 20)
        :param page: Page number (1-indexed, overrides offset)
        """
        cleaned_query = sql_query.strip()

        validation_error = self._validate_read_only_query(cleaned_query)
        if validation_error:
            return validation_error

        target_db = database_name or self.valves.DEFAULT_DATABASE
        row_limit = self._normalise_limit(limit)

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

    async def query_sales_performance(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sub_org: Optional[str] = None,
        zone: Optional[str] = None,
        brand_key: Optional[str] = None,
        customer_key: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query sales (Net Revenue, PC, UC) from dv.mlv_sale_preformance_aggregate.
        Filter: date (YYYY-MM-DD), sub_org, zone, brand_key, customer_key. Limit: 20.
        """
        where_clauses = []
        if date_from:
            where_clauses.append(f"BillingDate >= {self._sql_literal(date_from)}")
        if date_to:
            where_clauses.append(f"BillingDate <= {self._sql_literal(date_to)}")
        if sub_org:
            where_clauses.append(f"SubOrgKey = {self._sql_literal(sub_org)}")
        if zone:
            where_clauses.append(f"Zone LIKE {self._sql_literal(f'%{zone}%')}")
        if brand_key:
            where_clauses.append(f"BrandKey = {self._sql_literal(brand_key)}")
        if customer_key:
            where_clauses.append(f"BillCustomerKey = {self._sql_literal(customer_key)}")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT BillingDate, SubOrgKey, Zone, BrandKey, PackSizeKey, BillCustomerKey,
                   SumBillNetRevenue, SumBillPCVolume, SumBillUCVolume
            FROM dv.mlv_sale_preformance_aggregate
            {where_sql}
            ORDER BY BillingDate DESC
        """
        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_sales_targets(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        sub_org: Optional[str] = None,
        material_no: Optional[str] = None,
        customer_key: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query sales targets (Revenue, PC, UC) from dv.mlv_sale_target or dv.mlv_sale_target_customer.
        Filter: year, month, sub_org, material_no, customer_key. Limit: 20.
        """
        if customer_key:
            where_clauses = [f"CustomerKey = {self._sql_literal(customer_key)}"]
            if year:
                where_clauses.append(f"Year = {int(year)}")
            if month:
                where_clauses.append(f"MonthNumber = {int(month)}")
            where_sql = f"WHERE {' AND '.join(where_clauses)}"
            query = f"SELECT SubOrgKey, CustomerKey, MaterialNo, PackSizeCode, Year, MonthNumber, Revenue, Pc, Uc, MonthYearKey FROM dv.mlv_sale_target_customer {where_sql} ORDER BY Year DESC, MonthNumber DESC"
        else:
            where_clauses = []
            if year:
                where_clauses.append(f"Year = {int(year)}")
            if month:
                where_clauses.append(f"MonthNumber = {int(month)}")
            if sub_org:
                where_clauses.append(f"SubOrg = {self._sql_literal(sub_org)}")
            if material_no:
                where_clauses.append(f"MaterialNo = {self._sql_literal(material_no)}")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"SELECT MaterialNo, PackSizeCode, Year, MonthNumber, Revenue, Pc, Uc, SubOrg FROM dv.mlv_sale_target {where_sql} ORDER BY Year DESC, MonthNumber DESC"

        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_customers(
        self,
        customer_name: Optional[str] = None,
        customer_key: Optional[str] = None,
        search_term: Optional[str] = None,
        sub_org: Optional[str] = None,
        only_buying: bool = False,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query customers from gold.dim_customer or dv.mlv_buying_customer (only_buying=true).
        Filter: customer_name, customer_key, search_term, sub_org. Limit: 20.
        """
        if only_buying:
            where_clauses = []
            if customer_key:
                where_clauses.append(f"BillCustomerKey = {self._sql_literal(customer_key)}")
            if sub_org:
                where_clauses.append(f"SubOrgKey = {self._sql_literal(sub_org)}")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"SELECT BillingDate, BillCustomerKey, SalesGroupKey, SubOrgKey, SOSalesOfficeKey, IsHybrid FROM dv.mlv_buying_customer {where_sql} ORDER BY BillingDate DESC"
        else:
            where_clauses = []
            if customer_key:
                where_clauses.append(f"CustomerKey = {self._sql_literal(customer_key)}")
            if customer_name:
                name_pattern = self._sql_literal(f"%{customer_name}%")
                where_clauses.append(f"(Name LIKE {name_pattern} OR Name2 LIKE {name_pattern})")
            if search_term:
                where_clauses.append(f"SearchTerm LIKE {self._sql_literal(f'%{search_term}%')}")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"SELECT CustomerKey, Name, Name2, Country, Region, PostCode, SearchTerm, AcctGroup, CreatDate FROM gold.dim_customer {where_sql} ORDER BY CustomerKey"

        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_products(
        self,
        material_name: Optional[str] = None,
        material_key: Optional[str] = None,
        brand_key: Optional[str] = None,
        pack_size: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query products from gold.dim_material.
        Filter: material_name, material_key, brand_key, pack_size. Limit: 20.
        """
        where_clauses = []
        if material_key:
            where_clauses.append(f"MaterialKey = {self._sql_literal(material_key)}")
        if material_name:
            where_clauses.append(f"MatDescr LIKE {self._sql_literal(f'%{material_name}%')}")
        if brand_key:
            where_clauses.append(f"MatlGroup LIKE {self._sql_literal(f'%{brand_key}%')}")
        if pack_size:
            where_clauses.append(f"MatDescr LIKE {self._sql_literal(f'%{pack_size}%')}")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT MaterialKey, MatlNo, MatDescr, MatlTypeKey, MatlGroup, PackSizeKey, BrandKey, Status, CreatedOn FROM gold.dim_material {where_sql} ORDER BY MaterialKey"
        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_credit_and_overdue(
        self,
        customer_key: Optional[str] = None,
        due_before_date: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query overdue credit from dv.mlv_credit_overdue.
        Filter: customer_key, due_before_date (YYYY-MM-DD). Limit: 20.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"CustomerKey = {self._sql_literal(customer_key)}")
        if due_before_date:
            where_clauses.append(f"DueDate <= {self._sql_literal(due_before_date)}")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT CustomerKey, BillingDocKey, BaselineDate, DueDate, AmountLC, SignedAmount FROM dv.mlv_credit_overdue {where_sql} ORDER BY DueDate ASC"
        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_coolers(
        self,
        customer_key: Optional[str] = None,
        cooler_serial: Optional[str] = None,
        cooler_status: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query coolers from dv.mlv_outlet_with_cooler_buying.
        Filter: customer_key. Note: cooler_serial/status not supported; use query_fabric on dv.dv_cooler. Limit: 20.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"BillCustomerKey = {self._sql_literal(customer_key)}")

        if cooler_serial or cooler_status:
            return (
                "Error: cooler_serial and cooler_status are not available in "
                "dv.mlv_outlet_with_cooler_buying. Use get_table_schema on dv.dv_cooler "
                "and query_fabric with the required equipment fields."
            )
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT EquipmentKey, CustomerKey, ValidFromDate, ValidToDate, StorageLocationKey, BillCustomerKey, BillingDate FROM dv.mlv_outlet_with_cooler_buying {where_sql} ORDER BY BillingDate DESC, EquipmentKey"
        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_customer_visits(
        self,
        customer_key: Optional[str] = None,
        visit_date_from: Optional[str] = None,
        visit_date_to: Optional[str] = None,
        visit_group_key: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query customer visits from dv.mlv_customer_visit_list.
        Filter: customer_key, visit_date_from/to (YYYY-MM-DD), visit_group_key. Limit: 20.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"CustomerKey = {self._sql_literal(customer_key)}")
        if visit_date_from:
            where_clauses.append(f"ExecDateKey >= {self._sql_literal(visit_date_from)}")
        if visit_date_to:
            where_clauses.append(f"ExecDateKey <= {self._sql_literal(visit_date_to)}")
        if visit_group_key:
            where_clauses.append(f"VisitGroupKey = {self._sql_literal(visit_group_key)}")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT ExecDateKey, SubOrgKey, CustomerKey, VisitGroupKey, GroupVisitKey, GroupBM, GroupVisitSalesOfficeDescKey, GroupABM, SubOrgVisitGroupKey FROM dv.mlv_customer_visit_list {where_sql} ORDER BY ExecDateKey DESC, CustomerKey"
        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def query_customer_rfm(
        self,
        customer_key: Optional[str] = None,
        min_monetary: Optional[float] = None,
        segment: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query customer RFM segmentation from dv.mlv_customer_rfm.
        Filter: customer_key, min_monetary, segment (base_rfm_segment). Limit: 20.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"CustomerKey = {self._sql_literal(customer_key)}")
        if min_monetary is not None:
            where_clauses.append(f"cur_monetary >= {float(min_monetary)}")
        if segment:
            where_clauses.append(f"base_rfm_segment LIKE {self._sql_literal(f'%{segment}%')}")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT CustomerKey, BillCustomerKey, SalesGroupKey, cur_last_billing_date, cur_frequency, cur_monetary, cur_recency_days, base_rfm_segment, adjusted_rfm_segment, RFM_score, segment_health FROM dv.mlv_customer_rfm {where_sql} ORDER BY cur_monetary DESC, cur_frequency DESC"
        return await self.query_fabric(
            sql_query=query, limit=self._normalise_limit(limit), page=page, __user__=__user__
        )

    async def get_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = "gold",
        database_name: Optional[str] = None,
        limit: Optional[int] = 20,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Inspect columns from INFORMATION_SCHEMA.COLUMNS.
        :param table_name: Table/view name
        :param schema_name: Schema (default: gold). Limit: 20.
        """
        query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = {self._sql_literal(schema_name)}
                            AND TABLE_NAME = {self._sql_literal(table_name)}
            ORDER BY ORDINAL_POSITION
        """
        return await self.query_fabric(
            sql_query=query,
            database_name=database_name,
            limit=self._normalise_limit(limit),
            page=page,
            __user__=__user__,
        )

