#!/usr/bin/env python3
"""Sync the Procurement v2 workbook from SharePoint into Azure AI Search.

The SharePoint workbook is the only source of truth. The script downloads it to
an OS temporary directory, validates and normalizes awarded rows, then invokes
the existing Azure AI Search sync. It never stores the workbook in the repository.

Authentication precedence:
1. SHAREPOINT_ACCESS_TOKEN (delegated Microsoft Graph token)
2. MICROSOFT_CLIENT_* app-only client credentials

Required source location:
  SHAREPOINT_SITE_HOST, SHAREPOINT_SITE_PATH, SHAREPOINT_FILE_PATH
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests


HERE = Path(__file__).resolve().parent
BUILD_RECORDS = HERE / "build_search_records.py"
SYNC_SEARCH = HERE / "sync_azure_ai_search.py"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name}")
    return value


def graph_token() -> str:
    delegated = os.environ.get("SHAREPOINT_ACCESS_TOKEN", "").strip()
    if delegated:
        return delegated.removeprefix("Bearer ").strip()

    tenant_id = os.environ.get("MICROSOFT_CLIENT_TENANT_ID") or os.environ.get("MICROSOFT_TENANT", "")
    client_id = os.environ.get("MICROSOFT_CLIENT_ID", "")
    client_secret = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
    if not all((tenant_id, client_id, client_secret)):
        raise RuntimeError(
            "Set SHAREPOINT_ACCESS_TOKEN or MICROSOFT_CLIENT_TENANT_ID, "
            "MICROSOFT_CLIENT_ID, and MICROSOFT_CLIENT_SECRET"
        )

    response = requests.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def download_workbook(destination: Path) -> str:
    host = required("SHAREPOINT_SITE_HOST")
    site_path = required("SHAREPOINT_SITE_PATH").strip("/")
    file_path = required("SHAREPOINT_FILE_PATH").strip("/")
    headers = {"Authorization": f"Bearer {graph_token()}"}

    response = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{host}:/{site_path}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    site_id = response.json()["id"]

    response = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{file_path}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    item = response.json()

    response = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{item['id']}/content",
        headers=headers,
        timeout=90,
        allow_redirects=True,
    )
    response.raise_for_status()
    destination.write_bytes(response.content)
    return item.get("name", file_path)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="procurement_sharepoint_") as directory:
        temp_dir = Path(directory)
        workbook = temp_dir / "Procurement_Price_Template_v2.xlsx"
        records = temp_dir / "procurement_prices_for_search.jsonl"
        filename = download_workbook(workbook)
        print(f"Downloaded SharePoint source: {filename}")

        subprocess.run(
            [sys.executable, str(BUILD_RECORDS), "--source", str(workbook), "--output", str(records)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(SYNC_SEARCH), "--input", str(records)],
            check=True,
        )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, requests.RequestException, subprocess.CalledProcessError) as error:
        raise SystemExit(f"ERROR: {error}") from error
