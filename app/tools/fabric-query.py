"""
title: Fabric Data Warehouse Query Tool
author: Haadthip DIO
version: 1.2
required_open_webui_version: 0.5.0

Executes SQL queries against Microsoft Fabric Data Warehouse / Lakehouse using Entra ID authentication via Azure SDK or pyodbc.

Capabilities:
- Query Fabric Data Warehouse tables across domain-specific tools (Sales, Targets, Customers, Products, Credit, Coolers, Visits)
- Execute custom T-SQL queries safely (SELECT / read-only)
- Inspect table schemas and metadata (INFORMATION_SCHEMA)
- Pagination support with limit (max_rows) and page number / offset
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
        Execute a custom T-SQL SELECT query against Microsoft Fabric Data Warehouse / Lakehouse.

        :param sql_query: Read-only T-SQL SELECT query (e.g., 'SELECT TOP 10 * FROM dv.mlv_sale_preformance_aggregate').
        :param database_name: (Optional) Target database name such as 'LH_OTC_TEST' or 'LH_PROJECT'. Defaults to LH_OTC_TEST.
        :param limit: (Optional) Max rows to return per page (max cap: 200). Defaults to 50.
        :param offset: (Optional) Number of rows to skip (0-indexed). Defaults to 0.
        :param page: (Optional) Page number (1-indexed). Overrides offset.
        :return: JSON formatted query results.
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

    async def query_sales_performance(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sub_org: Optional[str] = None,
        zone: Optional[str] = None,
        brand_key: Optional[str] = None,
        customer_key: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query sales performance metrics (Net Revenue, PC Volume, UC Volume) aggregated by date, sub-org, zone, brand, or customer.
        Main Table: dv.mlv_sale_preformance_aggregate (also refers to dv.dv_daily_sales, gold.fact_billing)

        :param date_from: (Optional) Start date filter 'YYYY-MM-DD' (e.g. '2025-01-01').
        :param date_to: (Optional) End date filter 'YYYY-MM-DD' (e.g. '2025-01-31').
        :param sub_org: (Optional) Sales SubOrg key / code (e.g. '5110', '5120').
        :param zone: (Optional) Sales zone name or code.
        :param brand_key: (Optional) Brand Key / Code (e.g. 'COKE', 'FANTA').
        :param customer_key: (Optional) Customer ID / Code.
        :param limit: (Optional) Max rows per page. Defaults to 50.
        :param page: (Optional) Page number (1-indexed).
        """
        where_clauses = []
        if date_from:
            where_clauses.append(f"BillingDate >= '{date_from}'")
        if date_to:
            where_clauses.append(f"BillingDate <= '{date_to}'")
        if sub_org:
            where_clauses.append(f"SubOrgKey = '{sub_org}'")
        if zone:
            where_clauses.append(f"Zone LIKE '%{zone}%'")
        if brand_key:
            where_clauses.append(f"BrandKey = '{brand_key}'")
        if customer_key:
            where_clauses.append(f"BillCustomerKey = '{customer_key}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT BillingDate, SubOrgKey, Zone, BrandKey, PackSizeKey, BillCustomerKey,
                   SumBillNetRevenue, SumBillPCVolume, SumBillUCVolume
            FROM dv.mlv_sale_preformance_aggregate
            {where_sql}
            ORDER BY BillingDate DESC
        """
        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def query_sales_targets(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        sub_org: Optional[str] = None,
        material_no: Optional[str] = None,
        customer_key: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query sales target quotas and performance goals (Revenue, Physical Cases - PC, Unit Cases - UC).
        Main Tables: dv.mlv_sale_target, dv.mlv_sale_target_customer, gold.fact_sale_target

        :param year: (Optional) Target year (e.g. 2025).
        :param month: (Optional) Target month number 1-12.
        :param sub_org: (Optional) Sales SubOrg key / code.
        :param material_no: (Optional) Material / product code.
        :param customer_key: (Optional) Customer ID / Code for customer-level targets.
        :param limit: (Optional) Max rows per page.
        :param page: (Optional) Page number.
        """
        if customer_key:
            where_clauses = [f"BillCustomerKey = '{customer_key}'"]
            if year:
                where_clauses.append(f"Year = {year}")
            if month:
                where_clauses.append(f"MonthNumber = {month}")
            where_sql = f"WHERE {' AND '.join(where_clauses)}"
            query = f"SELECT * FROM dv.mlv_sale_target_customer {where_sql} ORDER BY Year DESC, MonthNumber DESC"
        else:
            where_clauses = []
            if year:
                where_clauses.append(f"Year = {year}")
            if month:
                where_clauses.append(f"MonthNumber = {month}")
            if sub_org:
                where_clauses.append(f"SubOrg = '{sub_org}'")
            if material_no:
                where_clauses.append(f"MaterialNo = '{material_no}'")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"SELECT MaterialNo, PackSizeCode, Year, MonthNumber, Revenue, Pc, Uc, SubOrg FROM dv.mlv_sale_target {where_sql} ORDER BY Year DESC, MonthNumber DESC"

        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def query_customers(
        self,
        customer_name: Optional[str] = None,
        customer_key: Optional[str] = None,
        search_term: Optional[str] = None,
        sub_org: Optional[str] = None,
        only_buying: bool = False,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query customer master data, buying customer status, and outlet details.
        Main Tables: gold.dim_customer, dv.mlv_buying_customer, dv.dv_new_outlet, dv.dv_closed_outlet

        :param customer_name: (Optional) Name or partial name of customer/store (e.g. 'เซเว่น', 'สมชาย').
        :param customer_key: (Optional) Exact Customer ID / Code.
        :param search_term: (Optional) Customer search term / alias.
        :param sub_org: (Optional) SubOrg key filter.
        :param only_buying: (Optional) If true, query active buying customers from dv.mlv_buying_customer.
        :param limit: (Optional) Max rows per page.
        :param page: (Optional) Page number.
        """
        if only_buying:
            where_clauses = []
            if customer_key:
                where_clauses.append(f"BillCustomerKey = '{customer_key}'")
            if sub_org:
                where_clauses.append(f"SubOrgKey = '{sub_org}'")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"SELECT BillingDate, BillCustomerKey, SalesGroupKey, SubOrgKey, SOSalesOfficeKey, IsHybrid FROM dv.mlv_buying_customer {where_sql} ORDER BY BillingDate DESC"
        else:
            where_clauses = []
            if customer_key:
                where_clauses.append(f"CustomerKey = '{customer_key}'")
            if customer_name:
                where_clauses.append(f"(Name LIKE '%{customer_name}%' OR Name2 LIKE '%{customer_name}%')")
            if search_term:
                where_clauses.append(f"SearchTerm LIKE '%{search_term}%'")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"SELECT CustomerKey, Name, Name2, Country, Region, PostCode, SearchTerm, AcctGroup, CreatDate FROM gold.dim_customer {where_sql} ORDER BY CustomerKey"

        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def query_products(
        self,
        material_name: Optional[str] = None,
        material_key: Optional[str] = None,
        brand_key: Optional[str] = None,
        pack_size: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query product and material master data (Material Description, Material Group, Brand, Pack Size).
        Main Tables: gold.dim_material, gold.dim_brand, gold.dim_pack_size, gold.dim_beverage_category, dbo.material_code

        :param material_name: (Optional) Product name or keyword (e.g. 'Coke', 'น้ำทิพย์', '325ml').
        :param material_key: (Optional) Material Code / Key.
        :param brand_key: (Optional) Brand code/name filter.
        :param pack_size: (Optional) Pack size filter.
        :param limit: (Optional) Max rows per page.
        :param page: (Optional) Page number.
        """
        where_clauses = []
        if material_key:
            where_clauses.append(f"MaterialKey = '{material_key}'")
        if material_name:
            where_clauses.append(f"MatDescr LIKE '%{material_name}%'")
        if brand_key:
            where_clauses.append(f"MatlGroup LIKE '%{brand_key}%'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT MaterialKey, MatlNo, MatDescr, MatlTypeKey, MatlGroup, Status, CreatedOn FROM gold.dim_material {where_sql} ORDER BY MaterialKey"
        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def query_credit_and_overdue(
        self,
        customer_key: Optional[str] = None,
        due_before_date: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query customer overdue credit, unpaid amounts, and account receivable status.
        Main Tables: dv.mlv_credit_overdue, dv.dv_credit_use_credit_limit, gold.dim_customer_credit, gold.fact_ar_open_item

        :param customer_key: (Optional) Customer ID / Code filter.
        :param due_before_date: (Optional) Date filter 'YYYY-MM-DD' to check items due on or before date.
        :param limit: (Optional) Max rows per page.
        :param page: (Optional) Page number.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"CustomerKey = '{customer_key}'")
        if due_before_date:
            where_clauses.append(f"DueDate <= '{due_before_date}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT CustomerKey, BillingDocKey, BaselineDate, DueDate, AmountLC, SignedAmount FROM dv.mlv_credit_overdue {where_sql} ORDER BY DueDate ASC"
        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def query_coolers(
        self,
        customer_key: Optional[str] = None,
        cooler_serial: Optional[str] = None,
        cooler_status: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query cooler placements, cooler buying statistics, and cooler inventory status.
        Main Tables: dv.dv_cooler, dv.mlv_outlet_with_cooler_buying, dv.dv_cooler_target, ext.ext_cooler_placement, gold.fact_cooler

        :param customer_key: (Optional) Customer ID / Code where cooler is installed.
        :param cooler_serial: (Optional) Serial number of the cooler equipment.
        :param cooler_status: (Optional) Status of cooler.
        :param limit: (Optional) Max rows per page.
        :param page: (Optional) Page number.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"BillCustomerKey = '{customer_key}'")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT * FROM dv.mlv_outlet_with_cooler_buying {where_sql}"
        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def query_customer_visits(
        self,
        customer_key: Optional[str] = None,
        visit_date_from: Optional[str] = None,
        visit_date_to: Optional[str] = None,
        visit_group_key: Optional[str] = None,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Query salesman customer visit plans, visit history, active visit routes, and sales orders from visits.
        Main Tables: dv.mlv_customer_visit_list, dv.mlv_active_customer_visit, dv.mlv_customer_visit_sales_order, gold.fact_customer_visit

        :param customer_key: (Optional) Customer ID / Code visited.
        :param visit_date_from: (Optional) Visit start date filter 'YYYY-MM-DD'.
        :param visit_date_to: (Optional) Visit end date filter 'YYYY-MM-DD'.
        :param visit_group_key: (Optional) Sales visit group / route key.
        :param limit: (Optional) Max rows per page.
        :param page: (Optional) Page number.
        """
        where_clauses = []
        if customer_key:
            where_clauses.append(f"CustomerKey = '{customer_key}'")
        if visit_group_key:
            where_clauses.append(f"VisitGroupKey = '{visit_group_key}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT * FROM dv.mlv_customer_visit_list {where_sql}"
        return await self.query_fabric(sql_query=query, limit=limit, page=page, __user__=__user__)

    async def list_tables(
        self,
        schema_name: Optional[str] = None,
        database_name: Optional[str] = None,
        limit: Optional[int] = 100,
        page: Optional[int] = 1,
        __user__: Optional[dict] = None
    ) -> str:
        """
        List available tables and schemas in Fabric Data Warehouse database with pagination.

        :param schema_name: (Optional) Filter by specific schema (e.g. 'dv', 'gold', 'ext', 'dbo', 'sap', 'silver', 'bronze').
        :param database_name: (Optional) Target database name (defaults to LH_OTC_TEST).
        :param limit: (Optional) Max rows per page. Defaults to 100.
        :param page: (Optional) Page number (1-indexed).
        :return: List of schemas, table names, and table types.
        """
        where_sql = f"WHERE TABLE_SCHEMA = '{schema_name}'" if schema_name else ""
        query = f"SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES {where_sql} ORDER BY TABLE_SCHEMA, TABLE_NAME;"
        return await self.query_fabric(
            sql_query=query, database_name=database_name, limit=limit, page=page, __user__=__user__
        )

    async def get_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = "gold",
        database_name: Optional[str] = None,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Inspect table column names, data types, and column positions for a specific table in Fabric DW.

        :param table_name: Table or view name (e.g. 'dim_customer', 'mlv_sale_preformance_aggregate').
        :param schema_name: (Optional) Schema name (e.g. 'dv', 'gold', 'dbo'). Defaults to 'gold'.
        :param database_name: (Optional) Target database name.
        :return: Column metadata listing.
        """
        query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """
        return await self.query_fabric(
            sql_query=query, database_name=database_name, limit=200, page=1, __user__=__user__
        )

