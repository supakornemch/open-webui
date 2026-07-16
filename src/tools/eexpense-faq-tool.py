"""
title: E-Expense FAQ Search (Tool)
author: Haadthip
version: 1.0
required_open_webui_version: 0.5.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Tool — E-Expense FAQ Search
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Searches the E-Expense FAQ index (eexpense-faq-idx) using hybrid search
(BM25 + vector + semantic) and returns the best matching answers.

Knowledge covered:
  • แผนการเดินทาง — ขอล่วงหน้า, ย้อนหลัง, One-day trip
  • การขอทดรองจ่าย — ระยะเวลา, เงื่อนไข
  • ผู้ร่วมเดินทาง — Cost Center, รวม/แยกเอกสาร
  • ค่าอาหาร/เบี้ยเลี้ยง — อัตรา Level 1-8, โรงแรม, วันหยุด
  • การแก้ไข/ยกเลิก — Withdraw, Terminate, Cancel Trip
  • การอนุมัติ — Approver, Delegate
  • Cost Center — แก้ไข, ดึงข้อมูล
  • สิทธิ์การเบิก — Outsource, ทำแทน, Requestor
  • ไฟล์แนบ — ประเภท, ขนาด
  • ข้อมูลระบบ — E-Expense คืออะไร, รองรับค่าใช้จ่ายอะไร
  • ประวัติเอกสาร — User Inbox, User History

How to use:
  1. Admin Settings → Functions → Add → paste this file → Save
  2. Go to Workspace → Models → select a model (e.g., deploy-gpt-5.4-mini)
  3. Enable the tool "search_eexpense_faq" (press 🔧 in chat)
  4. Start asking E-Expense questions!

The LLM will automatically call this tool when the user asks about E-Expense.
"""

import json
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from openai import AzureOpenAI


class Tools:
    class Valves(BaseModel):
        """Configuration — editable in Open WebUI Admin > Functions"""

        # ── Azure AI Search ──
        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
            description="Azure AI Search endpoint",
        )
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
            description="Search admin key",
        )
        index_name: str = Field(
            default="eexpense-faq-idx",
            description="E-Expense FAQ index name",
        )
        api_version: str = Field(
            default="2024-07-01",
            description="Search API version",
        )
        top_results: int = Field(
            default=5,
            description="Number of results to return",
        )

        # ── Azure OpenAI (for vector search) ──
        openai_endpoint: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
            description="Azure OpenAI endpoint (for embeddings)",
        )
        openai_api_key: str = Field(
            default=os.environ.get("OPENAI_API_KEY", ""),
            description="Azure OpenAI API key",
        )
        embedding_deployment: str = Field(
            default="deploy-embedding-3-large",
            description="Embedding deployment name",
        )
        embedding_dimensions: int = Field(
            default=3072,
            description="Embedding dimensions (3072 for 3-large)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._openai_client = None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN TOOL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def search_eexpense_faq(
        self,
        query: str,
        category: Optional[str] = None,
        condition: Optional[str] = None,
    ) -> str:
        """
        Search the E-Expense FAQ knowledge base for answers about Haadthip's
        E-Expense system (travel plans, expense claims, meal allowances, etc.)

        Use this tool when the user asks questions about:
        - การขอแผนการเดินทาง / travel plan requests
        - การขอทดรองจ่าย / cash advance
        - ค่าอาหาร เบี้ยเลี้ยง / meal allowances and rates
        - การอนุมัติ / approval process
        - การแก้ไข ยกเลิกเอกสาร / editing or canceling documents
        - Cost Center / ข้อมูลพนักงาน
        - ไฟล์แนบ / file attachments
        - สิทธิ์การเบิก / eligibility
        - E-Expense system overview

        Args:
            query: The user's question in Thai or English
            category: Optional — filter by category (e.g., "ค่าอาหาร/เบี้ยเลี้ยง",
                      "แผนการเดินทาง", "การขอทดรองจ่าย", "การอนุมัติ",
                      "การแก้ไข/ยกเลิกเอกสาร", "สิทธิ์การเบิก", "Cost Center",
                      "ผู้ร่วมเดินทาง", "ไฟล์แนบ", "ข้อมูลระบบ", "ประวัติเอกสาร")
            condition: Optional — filter by conditions (e.g., "มีขอทดรองจ่าย",
                      "Cost Center เดียวกัน", "Level 5")

        Returns:
            JSON string with search results: question, answer, category, conditions
        """
        url = (
            f"{self.valves.search_endpoint}/indexes/"
            f"{self.valves.index_name}/docs/search"
            f"?api-version={self.valves.api_version}"
        )

        payload = {
            "search": query,
            "top": self.valves.top_results,
            "queryType": "semantic",
            "semanticConfiguration": "eexpense-semantic-config",
            "select": "id,question,answer,shortAnswer,category,conditions,sourceId,contextQuestions",
        }

        # Build filter
        filters = []
        if category:
            filters.append(f"category eq '{category}'")
        if condition:
            filters.append(f"conditions/any(c: search.in(c, '{condition}'))")
        if filters:
            payload["filter"] = " and ".join(filters)

        # Add vector search if OpenAI client available
        client = self._get_openai_client()
        if client:
            try:
                resp = client.embeddings.create(
                    model=self.valves.embedding_deployment,
                    input=[query],
                    dimensions=self.valves.embedding_dimensions,
                )
                vector = resp.data[0].embedding
                payload["vectorQueries"] = [{
                    "vector": vector,
                    "fields": "contentVector",
                    "kind": "vector",
                    "k": self.valves.top_results,
                }]
            except Exception:
                pass  # fall back to text-only search

        headers = {
            "Content-Type": "application/json",
            "api-key": self.valves.search_api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code != 200:
                # Fallback: retry without semantic
                payload.pop("queryType", None)
                payload.pop("semanticConfiguration", None)
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code != 200:
                return json.dumps({
                    "error": f"Search failed: {resp.status_code}",
                    "detail": resp.text[:300],
                }, ensure_ascii=False)

            data = resp.json()
            docs = data.get("value", [])

            if not docs:
                return json.dumps({
                    "message": "ไม่พบข้อมูลเกี่ยวกับคำถามนี้ในระบบ E-Expense",
                    "suggestion": "ลองถามคำถามอื่น หรือติดต่อ IT Service โครงการ E-Expense",
                }, ensure_ascii=False)

            # Format results
            results = []
            for doc in docs:
                conditions = doc.get("conditions", [])
                result = {
                    "question": doc.get("question", ""),
                    "answer": doc.get("answer", ""),
                    "shortAnswer": doc.get("shortAnswer", ""),
                    "category": doc.get("category", ""),
                    "sourceId": doc.get("sourceId", ""),
                }
                if conditions:
                    result["เงื่อนไข"] = conditions
                if doc.get("contextQuestions"):
                    result["เส้นทางคำถาม"] = doc.get("contextQuestions")
                results.append(result)

            return json.dumps({
                "query": query,
                "total_results": len(results),
                "results": results,
                "note": (
                    "ถ้ามี 'เงื่อนไข' — คำตอบนี้ขึ้นอยู่กับเงื่อนไขที่ระบุ "
                    "กรุณาถามผู้ใช้เพิ่มเติมหากข้อมูลไม่ครบ"
                ),
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Search error: {str(e)[:200]}",
            }, ensure_ascii=False)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_openai_client(self):
        """Lazy-init Azure OpenAI client for embeddings."""
        if self._openai_client is None and self.valves.openai_api_key:
            try:
                self._openai_client = AzureOpenAI(
                    api_key=self.valves.openai_api_key,
                    api_version="2024-12-01-preview",
                    azure_endpoint=self.valves.openai_endpoint,
                )
            except Exception:
                pass
        return self._openai_client
