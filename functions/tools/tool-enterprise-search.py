"""
title: Enterprise Search (Tool)
author: Haadthip DIO
version: 1.0
required_open_webui_version: 0.1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Tool — Unified Enterprise Document Search
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Queries enterprise-docs-idx (Azure AI Search) across 3 corpuses:
  • search_internal_docs  — IT Policy, MFA, VPN, Email, Meeting, HR Policies, Forms
  • search_hr_policies    — HR announcements, benefits, regulations, training
  • search_openwebui_help — Open WebUI features, API, setup guides

v1.0: Direct index search (replaces KB-based tools).
      Uses hybrid search: BM25 + vector + semantic.

Setup:
  1. Admin → Functions → + → paste → Save → enable
  2. Model → Native Mode → enable this tool
"""

import json
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
            description="Azure AI Search endpoint",
        )
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
            description="Search admin key",
        )
        index_name: str = Field(
            default="enterprise-docs-idx",
            description="Search index name",
        )
        max_results: int = Field(
            default=5, description="Max results per search", ge=1, le=10
        )
        search_timeout: int = Field(
            default=30, description="Search timeout (seconds)"
        )

    def __init__(self):
        self.valves = self.Valves()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Search Tools
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def search_internal_docs(
        self,
        query: str,
        corpus: str = "",
        category: str = "",
    ) -> str:
        """
        Search Haadthip internal documents: IT policies (MFA, VPN, Email),
        meeting room guides, corporate security, DLP, and HR policies.

        Use when user asks about:
        - IT systems: MFA setup, VPN connection, Email O365, SpamTitan
        - Meeting room booking, security policies, DLP
        - Company regulations, announcements, benefits, leave policies
        - Any internal work procedure or policy

        :param query: Search query in Thai or English
        :param corpus: Filter by corpus — "corporate" or "hr-policies" (leave empty for all)
        :param category: Filter by document category เช่น "IT Policy","Security Manual","HR Policy" (leave empty for all)
        """
        return await self._search(query, corpus or "corporate,hr-policies", category)

    async def search_hr_policies(
        self,
        query: str,
        category: str = "",
    ) -> str:
        """
        Search HR-only documents: policies, announcements, forms,
        benefits, training, PDPA, social security, regulations.

        Use when user asks about:
        - Leave/vacation policies, benefits, welfare
        - Training courses, competency guides
        - Recruitment, appointment orders
        - Provident fund, social security, medical claims
        - Employee regulations, code of conduct

        :param query: Search query in Thai
        :param category: Filter by document category เช่น "Policy","Benefits & Welfare","Training & Development" (leave empty for all)
        """
        return await self._search(query, "hr-policies", category)

    async def search_openwebui_help(
        self,
        query: str,
        category: str = "",
    ) -> str:
        """
        Search Open WebUI documentation: features, API endpoints,
        setup guides, extensibility, Pipelines, Tools, MCP.

        Use when user asks:
        - How to use Open WebUI features (chat, RAG, models, tools)
        - API reference: chat completions, model management, files
        - Setup: Docker, Kubernetes, SSO, RBAC
        - How to create Pipes, Tools, Functions, Filters

        :param query: Search query in English or Thai
        :param category: Filter by category (leave empty for all)
        """
        return await self._search(query, "openwebui-docs", category)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Shared search implementation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _search(
        self, query: str, corpus_filter: str, category_filter: str = ""
    ) -> str:
        """Direct index search with corpus + category filter + semantic ranking."""
        key = self.valves.search_api_key or os.environ.get(
            "AZURE_SEARCH_ADMIN_KEY", ""
        )
        if not key:
            return "⚠️ Missing search_api_key in valves or env"

        url = (
            f"{self.valves.search_endpoint}/indexes/{self.valves.index_name}"
            f"/docs/search?api-version=2024-07-01"
        )

        # Build filter: corpus + optional category
        filters = []
        corpuses = [c.strip() for c in corpus_filter.split(",") if c.strip()]
        if len(corpuses) == 1:
            filters.append(f"corpus eq '{corpuses[0]}'")
        elif len(corpuses) > 1:
            parts = " or ".join(f"corpus eq '{c}'" for c in corpuses)
            filters.append(f"({parts})")

        if category_filter:
            cats = [c.strip() for c in category_filter.split(",") if c.strip()]
            if len(cats) == 1:
                filters.append(f"category eq '{cats[0]}'")
            elif len(cats) > 1:
                parts = " or ".join(f"category eq '{c}'" for c in cats)
                filters.append(f"({parts})")

        filter_str = " and ".join(filters) if filters else ""

        body = {
            "search": query,
            "filter": filter_str,
            "queryType": "semantic",
            "semanticConfiguration": "semantic-config",
            "searchFields": "content,summary,file_name,category",
            "select": "file_name,corpus,category,content,summary,meta",
            "top": self.valves.max_results,
            "captions": "extractive",
            "answers": "extractive|count-1",
        }

        async with httpx.AsyncClient(timeout=self.valves.search_timeout) as client:
            try:
                resp = await client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json", "api-key": key},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                return f"⚠️ Search error: {e}"

        # Extract answer if available
        answer_text = ""
        if data.get("@search.answers"):
            answer_text = data["@search.answers"][0].get("text", "")

        # Format results
        docs = []
        for doc in data.get("value", []):
            file_name = doc.get("file_name", "Untitled")
            category = doc.get("category", "")
            summary = doc.get("summary", "")
            content = doc.get("content", "")[:400]
            caption = ""
            if doc.get("@search.captions"):
                caption = doc["@search.captions"][0].get("text", "")
            text = caption or content
            header = f"[{category}] {file_name}"
            if summary and summary not in text:
                text = f"{summary}\n{text}"
            docs.append(f"{header}\n{text}")

        result = "\n\n---\n\n".join(docs) if docs else "ไม่พบเอกสาร"

        # Prepend answer if available
        if answer_text:
            result = f"📝 **Answer:** {answer_text}\n\n---\n\n{result}"

        return result if result.strip() else "ไม่พบเอกสารที่เกี่ยวข้อง"
