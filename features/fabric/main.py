import os
import struct
import pyodbc
from azure.identity import DefaultAzureCredential, AzureCliCredential

# 1. Endpoint & DB Configuration
endpoint = os.getenv("FABRIC_ENDPOINT")
database = "LH_OTC_TEST"

if not endpoint:
    raise ValueError("FABRIC_ENDPOINT environment variable is not set. Please set it to the Fabric Data Warehouse Endpoint server hostname." )
# 2. Acquire Entra ID Token using Azure SDK
try:
    credential = DefaultAzureCredential()
    token = credential.get_token("https://database.windows.net/.default")
except Exception:
    credential = AzureCliCredential()
    token = credential.get_token("https://database.windows.net/.default")

# 3. Format Access Token for ODBC Attribute 1256 (SQL_COPT_SS_ACCESS_TOKEN)
token_bytes = token.token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
SQL_COPT_SS_ACCESS_TOKEN = 1256

# 4. Connection string
conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server={endpoint},1433;"
    f"Database={database};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)

conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        COUNT(*) AS TotalRows,
        MIN(BillingDate) AS MinDate,
        MAX(BillingDate) AS MaxDate,
        SUM(SumBillNetRevenue) AS TotalNetRevenue,
        SUM(SumBillPCVolume) AS TotalPCVolume,
        SUM(SumBillUCVolume) AS TotalUCVolume
    FROM dv.mlv_sale_preformance_aggregate
""")

row = cursor.fetchone()
print("Summary Statistics:")
print(f"Total Rows: {row.TotalRows:,}")
print(f"Date Range: {row.MinDate} to {row.MaxDate}")
print(f"Total Net Revenue (SumBillNetRevenue): {row.TotalNetRevenue:,.2f}")
print(f"Total PC Volume (SumBillPCVolume): {row.TotalPCVolume:,.3f}")
print(f"Total UC Volume (SumBillUCVolume): {row.TotalUCVolume:,.3f}")

conn.close()