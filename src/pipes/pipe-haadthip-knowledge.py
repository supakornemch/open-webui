"""
title: Haadthip Enterprise Knowledge (Pipe)
author: Haadthip
version: 2.0
required_open_webui_version: 0.1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Pipe — Agentic Retrieval via Azure AI Search
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replaces all old tools (tool-haadthip-docs, tool-sap-knowledge, openwebui-kb-tool)
with a single Pipe function that routes queries across all 3 Knowledge Sources.

Knowledge Sources (all via haadthip-kb):
  • haadthip-ks  — Corporate docs: Security, Email, Meeting Room, IT Policy, Public Disclosure
  • sap-docs-ks   — SAP HIP manuals: Tcodes, procedures, branch operations
  • ir-docs-ks    — Investor Relations: Annual Reports, Financial Data, Company Disclosures

How it works:
  1. User sends a query in Open WebUI
  2. Pipe calls Azure AI Search Knowledge Base (agentic retrieval)
  3. KB automatically: decomposes query → searches relevant sources → ranks results
  4. Pipe passes search results + context to Azure OpenAI for final answer
  5. Response includes citations and source document titles

Install in Open WebUI:
  Admin Settings → Functions → + → paste this file → Save
  Then select "Haadthip Enterprise Knowledge (Pipe)" as the model
"""

import asyncio
import json
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        """Configuration — editable in Open WebUI Admin > Functions"""

        # ── Azure AI Search ──
        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
            description="Azure AI Search endpoint",
        )
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
            description="Search admin key (auto-detected from env)",
        )
        kb_name: str = Field(
            default="haadthip-kb",
            description="Knowledge Base name",
        )
        ks_names: str = Field(
            default="haadthip-ks,sap-docs-ks,ir-docs-ks",
            description="Knowledge Sources (comma-separated)",
        )
        max_output_tokens: int = Field(
            default=8000, description="Max output tokens for KB retrieve"
        )
        search_timeout: int = Field(
            default=90, description="Search timeout in seconds"
        )

        # ── Azure OpenAI ──
        azure_endpoint: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
            description="Azure OpenAI endpoint",
        )
        azure_api_key: str = Field(
            default=os.environ.get("OPENAI_API_KEY", ""),
            description="Azure OpenAI key",
        )
        deployment_name: str = Field(
            default="deploy-gpt-5.4",  # gpt-5.4 for generation (not nano)
            description="LLM deployment for final answer generation",
        )
        kb_model_name: str = Field(
            default="deploy-gpt-5.4-nano",
            description="LLM used by KB for query planning (set in KB config, not here)",
        )
        api_version: str = Field(
            default="2024-12-01-preview",
            description="Azure OpenAI API version",
        )

    class UserValves(BaseModel):
        show_full_content: bool = Field(
            default=False, description="Show full document content (vs 300 char snippet)"
        )
        max_results: int = Field(
            default=5, description="Max results to include in context", ge=1, le=15
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "haadthip-knowledge"
        self.name = "Haadthip Enterprise Knowledge (Pipe)"
        self.valves = self.Valves()
        self.user_valves = self.UserValves()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN PIPE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def pipe(
        self,
        body: dict,
        __user__: dict,
        __metadata__: dict,
        __event_emitter__: Any = None,
        __task__: Any = None,
    ) -> str:
        messages = body.get("messages", [])
        if not messages:
            return "No messages provided"

        # Extract last user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        if not last_user_msg:
            return "กรุณาใส่คำถาม"

        # Get config from valves (with env fallback)
        search_key = self.valves.search_api_key or os.environ.get(
            "AZURE_SEARCH_ADMIN_KEY", ""
        )
        openai_key = self.valves.azure_api_key or os.environ.get(
            "AZURE_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "")
        )
        if not search_key:
            return "❌ Missing search_api_key in Valves or AZURE_SEARCH_ADMIN_KEY env"
        if not openai_key:
            return "❌ Missing azure_api_key in Valves or AZURE_OPENAI_API_KEY env"

        await self._emit(__event_emitter__, "status", {
            "description": "🔍 กำลังค้นหาจากคลังความรู้...", "done": False
        })

        try:
            # Step 1: Agentic Retrieval
            search_results = await self._retrieve(
                query=last_user_msg, search_key=search_key
            )

            found = len(search_results.get("docs", []))
            await self._emit(__event_emitter__, "status", {
                "description": f"📄 พบ {found} เอกสาร → กำลังสรุป...", "done": False
            })

            # Step 2: Generate answer with LLM
            response = await self._generate(
                user_query=last_user_msg,
                search_results=search_results,
                message_history=messages,
                openai_key=openai_key,
            )

            await self._emit(__event_emitter__, "status", {"description": "✅ เสร็จ", "done": True})
            return response

        except httpx.ConnectTimeout:
            await self._emit(__event_emitter__, "status", {"description": "❌ Search timeout", "done": True})
            return "⚠️ ไม่สามารถเชื่อมต่อ AI Search ได้ — กรุณาลองใหม่ (timeout)"
        except httpx.HTTPStatusError as e:
            await self._emit(__event_emitter__, "status", {"description": f"❌ HTTP {e.response.status_code}", "done": True})
            return f"⚠️ Search error (HTTP {e.response.status_code}): {e.response.text[:200]}"
        except Exception as e:
            await self._emit(__event_emitter__, "status", {"description": f"❌ Error: {str(e)[:50]}", "done": True})
            return f"⚠️ เกิดข้อผิดพลาด: {str(e)[:300]}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: Agentic Retrieval via KB
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _retrieve(self, query: str, search_key: str) -> dict:
        """Search Knowledge Base via agentic retrieval API."""
        ks_names = [s.strip() for s in self.valves.ks_names.split(",") if s.strip()]
        ks_params = [
            {"knowledgeSourceName": ks, "kind": "searchIndex"} for ks in ks_names
        ]

        url = (
            f"{self.valves.search_endpoint}/knowledgebases('{self.valves.kb_name}')"
            f"/retrieve?api-version=2026-04-01"
        )
        payload = {
            "intents": [{"search": query, "type": "semantic"}],
            "knowledgeSourceParams": ks_params,
            "maxOutputSizeInTokens": max(self.valves.max_output_tokens, 5000),
        }

        async with httpx.AsyncClient(timeout=self.valves.search_timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "api-key": search_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Parse activities (search logs)
        activities = []
        for act in data.get("activity", []):
            act_type = act.get("type", "")
            if act_type == "searchIndex":
                ks_name = act.get("knowledgeSourceName", "?")
                count = act.get("count", 0)
                elapsed = act.get("elapsedMs", 0)
                # Friendly names
                if "haadthip" in ks_name and "public" in ks_name:
                    label = "📋 Corporate Docs"
                elif "sap" in ks_name:
                    label = "📘 SAP Manuals"
                elif "ir" in ks_name:
                    label = "📊 IR Documents"
                else:
                    label = ks_name
                activities.append(f"{label}: {count} results ({elapsed}ms)")
            elif act_type == "modelQueryPlanning":
                activities.append(
                    f"🧠 Query planning: {act.get('inputTokens', 0)}→{act.get('outputTokens', 0)} tokens"
                )

        # Parse documents
        docs = []
        raw_docs = []
        for resp_item in data.get("response", []):
            for content in resp_item.get("content", []):
                if content.get("type") != "text":
                    continue
                text_val = content.get("text", "")
                if not text_val or text_val == "[]":
                    continue
                try:
                    results = json.loads(text_val)
                    if isinstance(results, list):
                        for doc in results[: self.user_valves.max_results]:
                            title = doc.get("title", "Untitled")
                            doc_content = doc.get("content", "")
                            if not self.user_valves.show_full_content:
                                doc_content = (
                                    doc_content[:300] + "..."
                                    if len(doc_content) > 300
                                    else doc_content
                                )
                            docs.append(f"### [{title}]\n{doc_content}")
                        raw_docs.extend(results[: self.user_valves.max_results])
                except (json.JSONDecodeError, TypeError):
                    pass

        return {"docs": docs, "activities": activities, "raw_docs": raw_docs, "raw": data}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: LLM Generation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _generate(
        self,
        user_query: str,
        search_results: dict,
        message_history: list,
        openai_key: str,
    ) -> str:
        """Generate final answer with Azure OpenAI, grounded in search results."""

        # Build context
        context_parts = []

        # Search activity summary
        if search_results["activities"]:
            context_parts.append(
                "### 📊 Search Activity\n" + "\n".join(search_results["activities"])
            )

        # Document results
        if search_results["docs"]:
            context_parts.append(
                "### 📄 เอกสารที่เกี่ยวข้อง\n\n" + "\n\n".join(search_results["docs"])
            )
        else:
            context_parts.append(
                "### ⚠️ ไม่พบเอกสาร\nไม่พบเอกสารที่เกี่ยวข้องจากคลังความรู้ของบริษัท"
            )

        context = "\n\n".join(context_parts)
        has_docs = len(search_results.get("docs", [])) > 0

        # Detect domain from results
        has_sap = any(
            "sap" in (d.get("terms", "") or "").lower()
            for d in search_results.get("raw_docs", [])
        )
        has_ir = any(
            "ir" in (d.get("terms", "") or "").lower()
            for d in search_results.get("raw_docs", [])
        )

        source_hint = ""
        if has_docs:
            source_hint = "ด้านล่างนี้คือเอกสารที่เกี่ยวข้องที่ค้นพบจากคลังความรู้ของบริษัท"
            if has_sap:
                source_hint += " (รวมถึง SAP HIP Manuals)"
            if has_ir:
                source_hint += " (รวมถึง Investor Relations)"
            source_hint += ":"
        else:
            source_hint = (
                "⚠️ ไม่พบเอกสารที่เกี่ยวข้องจากคลังความรู้ของบริษัท — "
                "ให้ตอบตามความรู้ทั่วไปของคุณ แต่แจ้งผู้ใช้ว่าไม่พบในเอกสารของบริษัท"
            )

        system_prompt = f"""คุณคือ **ผู้ช่วยอัจฉริยะของบริษัท หาดทิพย์ จำกัด (มหาชน)** (Haadthip Enterprise Assistant)

{source_hint}

{context}

## คำแนะนำในการตอบ
- **ตอบเป็นภาษาไทย** ยกเว้นศัพท์เทคนิคที่ควรเป็นภาษาอังกฤษ
- **ยึดเนื้อหาจากเอกสารเป็นหลัก** — สรุปเฉพาะข้อมูลที่มีในเอกสาร อย่าแต่งเติม
- **อ้างอิงแหล่งที่มา** — ใส่ [ชื่อเอกสาร] ทุกครั้งที่ใช้ข้อมูลจากเอกสาร
- ถ้าเอกสารมีขั้นตอน → สรุปเป็นข้อๆ เรียงตามลำดับ
- ถ้าเกี่ยวกับ SAP → ระบุ Tcode ด้วย
- ถ้าเป็นข้อมูลการเงิน/One Report → ระบุปีของรายงานด้วย
- ไม่ต้องถามกลับ — ตอบให้ตรงประเด็น
- หากไม่มีข้อมูลเพียงพอ → บอกผู้ใช้ตามตรงว่าไม่พบในเอกสาร พร้อมแนะนำแหล่งอื่นที่อาจมีข้อมูล"""

        # Build LLM messages
        llm_messages = [{"role": "system", "content": system_prompt}]
        # Add last few messages for conversation context
        for msg in message_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            llm_messages.append({"role": role, "content": content})

        url = (
            f"{self.valves.azure_endpoint}/openai/deployments/"
            f"{self.valves.deployment_name}/chat/completions"
            f"?api-version={self.valves.api_version}"
        )

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                url,
                json={
                    "messages": llm_messages,
                    "temperature": 0.3,  # Lower = more grounded
                    "max_completion_tokens": 4096,
                    "stream": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "api-key": openai_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _emit(self, emitter: Any, event_type: str, data: dict):
        """Emit status events to Open WebUI."""
        if emitter and hasattr(emitter, "__call__"):
            await emitter({"type": event_type, "data": data})

    async def get_models(self) -> list[dict]:
        """Register as an available 'model' in Open WebUI."""
        return [
            {
                "id": "haadthip-knowledge",
                "name": "Haadthip Enterprise Knowledge (Pipe)",
            }
        ]
