"""
title: Haadthip Knowledge Search (Tool)
author: Haadthip
version: 2.1
required_open_webui_version: 0.1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Tool — Multi-Source Knowledge Search
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5 search tools for model Native/Agentic Mode function calling:
  • search_corporate_knowledge — IT Policy, MFA, VPN, Email, Meeting Room
  • search_sap_knowledge        — SAP HIP Manuals, Tcodes
  • search_ir_knowledge         — Investor Relations, Annual Reports, Financial Data
  • search_hr_knowledge         — HR Policies, Forms, Manuals, Regulations
  • search_eexpense             — E-Expense FAQ

v2.1: Calls Azure AI Search directly (KB agentic retrieval + index search).
      LLM chat traffic still goes through LiteLLM for token tracking.
      ponytail: LiteLLM v1.83.3 vector_store_registry routing is broken
      (defaults to OpenAI provider). Revisit when LiteLLM fixes vector store
      routing — then switch tool to LiteLLM /v1/vector_stores/{name}/search.

Setup:
  1. Admin → Functions → + → paste this file → Save → enable
  2. Workspace → Models → gpt-5.4-mini → Native mode
  3. In chat, click 🔧 → enable desired tools
"""

import json
import os
from typing import Any

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
        kb_name: str = Field(
            default="haadthip-kb", description="Knowledge Base name"
        )
        eexpense_index: str = Field(
            default="eexpense-faq-idx", description="E-Expense FAQ index"
        )
        max_results: int = Field(
            default=5, description="Max documents per search", ge=1, le=10
        )
        search_timeout: int = Field(
            default=90, description="Search timeout in seconds"
        )

    def __init__(self):
        self.valves = self.Valves()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # KB-based searches (via Agentic Retrieval)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def search_corporate_knowledge(self, query: str) -> str:
        """
        Search Haadthip corporate IT documents: MFA, VPN, Email O365,
        Meeting Room booking, IT Policy, public disclosures.

        Use when user asks about IT systems, security, email setup,
        meeting rooms, or company policies.

        :param query: Search query in Thai or English
        """
        return await self._retrieve_kb(query, "haadthip-ks")

    async def search_sap_knowledge(self, query: str) -> str:
        """
        Search SAP HIP manuals: Tcodes, procedures, branch operations.

        Use when user asks about SAP transactions, stock checking,
        asset reporting, or any SAP-related workflow.

        :param query: Search query, can include Tcode (e.g. mb52, fiar06)
        """
        return await self._retrieve_kb(query, "sap-docs-ks")

    async def search_ir_knowledge(self, query: str) -> str:
        """
        Search Investor Relations documents: Annual Reports (One Report),
        Form 56-1, Financial Data, MD&A, AGM Minutes.

        Use when user asks about financial results, shareholder structure,
        corporate governance, sustainability, or company performance.

        :param query: Search query in Thai or English
        """
        return await self._retrieve_kb(query, "ir-docs-ks")

    async def search_hr_knowledge(self, query: str) -> str:
        """
        Search HR documents: policies, forms, manuals, regulations,
        announcements from MiHCM system.

        Use when user asks about leave, benefits, compensation,
        work rules, or employee rights.

        :param query: Search query in Thai or English
        """
        return await self._retrieve_kb(query, "mihcm-hr-ks")

    async def search_eexpense(self, query: str) -> str:
        """
        Search E-Expense FAQ: travel plans, advance payments,
        expense clearing, medical claims, approval workflows.

        Use when user asks about E-Expense system procedures,
        allowance rates, or expense claim steps.

        :param query: Search query in Thai
        """
        search_key = self.valves.search_api_key or os.environ.get(
            "AZURE_SEARCH_ADMIN_KEY", ""
        )
        if not search_key:
            return "⚠️ Missing search_api_key"

        url = (
            f"{self.valves.search_endpoint}/indexes/{self.valves.eexpense_index}"
            f"/docs/search?api-version=2024-07-01"
        )
        async with httpx.AsyncClient(timeout=self.valves.search_timeout) as client:
            resp = await client.post(
                url,
                json={
                    "search": query,
                    "queryType": "semantic",
                    "semanticConfiguration": "eexpense-semantic-config",
                    "top": self.valves.max_results,
                    "select": "question,answer,category,keywords",
                    "searchFields": "question,answer,keywords",
                },
                headers={
                    "Content-Type": "application/json",
                    "api-key": search_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        docs = []
        for doc in data.get("value", []):
            question = doc.get("question", "?")
            answer = doc.get("answer", "")
            category = doc.get("category", "")
            docs.append(f"[{category}] {question}\n{answer[:500]}")

        return "\n\n".join(docs) if docs else "ไม่พบคำตอบใน FAQ E-Expense"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Shared KB retrieval
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _retrieve_kb(self, query: str, ks_name: str) -> str:
        """Shared Knowledge Base retrieval for all KB-based searches."""
        search_key = self.valves.search_api_key or os.environ.get(
            "AZURE_SEARCH_ADMIN_KEY", ""
        )
        if not search_key:
            return "⚠️ Missing search_api_key"

        url = (
            f"{self.valves.search_endpoint}/knowledgebases('{self.valves.kb_name}')"
            f"/retrieve?api-version=2026-04-01"
        )
        async with httpx.AsyncClient(timeout=self.valves.search_timeout) as client:
            resp = await client.post(
                url,
                json={
                    "intents": [{"search": query, "type": "semantic"}],
                    "knowledgeSourceParams": [
                        {"knowledgeSourceName": ks_name, "kind": "searchIndex"}
                    ],
                    "maxOutputSizeInTokens": 5000,
                },
                headers={
                    "Content-Type": "application/json",
                    "api-key": search_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        docs = []
        for resp_item in data.get("response", []):
            for c in resp_item.get("content", []):
                if c.get("type") != "text":
                    continue
                try:
                    results = json.loads(c.get("text", "[]"))
                    if isinstance(results, list):
                        for doc in results[: self.valves.max_results]:
                            title = doc.get("title", "Untitled")
                            content = doc.get("content", "")[:500]
                            docs.append(f"[{title}]\n{content}")
                except (json.JSONDecodeError, TypeError):
                    pass

        return "\n\n".join(docs) if docs else "ไม่พบเอกสารในคลังความรู้"
