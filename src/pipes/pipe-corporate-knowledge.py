"""
title: Haadthip Corporate Knowledge (Pipe)
author: Haadthip
version: 1.0
required_open_webui_version: 0.1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Pipe — Corporate Docs (IT Policy, Security, Email, Meeting Room)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Knowledge Sources:
  • haadthip-ks — Corporate docs: Security, Email, Meeting Room, IT Policy, Public Disclosure

Install in Open WebUI:
  Admin Settings → Functions → + → paste this file → Save
  Then select "Haadthip Corporate Knowledge (Pipe)" as the model
"""

import json
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        """Configuration — editable in Open WebUI Admin > Functions"""

        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
            description="Azure AI Search endpoint",
        )
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
            description="Search admin key (auto-detected from env)",
        )
        kb_name: str = Field(
            default="haadthip-kb", description="Knowledge Base name"
        )
        max_output_tokens: int = Field(
            default=8000, description="Max output tokens for KB retrieve"
        )
        search_timeout: int = Field(
            default=90, description="Search timeout in seconds"
        )
        azure_endpoint: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
            description="Azure OpenAI endpoint",
        )
        azure_api_key: str = Field(
            default=os.environ.get("OPENAI_API_KEY", ""),
            description="Azure OpenAI key",
        )
        deployment_name: str = Field(
            default="deploy-gpt-5.4",
            description="LLM deployment for final answer generation",
        )
        api_version: str = Field(
            default="2024-12-01-preview",
            description="Azure OpenAI API version",
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "haadthip-corporate-knowledge"
        self.name = "Haadthip Corporate Knowledge (Pipe)"
        self.valves = self.Valves()

    async def pipe(
        self, body: dict, __user__: dict, __metadata__: dict,
        __event_emitter__: Any = None, __task__: Any = None,
    ) -> str:
        messages = body.get("messages", [])
        if not messages:
            return "No messages provided"

        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        if not last_user_msg:
            return "กรุณาใส่คำถาม"

        search_key = self.valves.search_api_key or os.environ.get("AZURE_SEARCH_ADMIN_KEY", "")
        openai_key = self.valves.azure_api_key or os.environ.get("OPENAI_API_KEY", "")
        if not search_key:
            return "❌ Missing search_api_key"
        if not openai_key:
            return "❌ Missing azure_api_key"

        await self._emit(__event_emitter__, "status", {
            "description": "🔍 กำลังค้นหาจากคลังความรู้องค์กร...", "done": False
        })

        try:
            # Step 1: Retrieve — only corporate KS
            search_results = await self._retrieve(query=last_user_msg, search_key=search_key)
            found = len(search_results.get("docs", []))
            await self._emit(__event_emitter__, "status", {
                "description": f"📄 พบ {found} เอกสาร → กำลังสรุป...", "done": False
            })
            # Step 2: Generate
            response = await self._generate(
                user_query=last_user_msg, search_results=search_results,
                message_history=messages, openai_key=openai_key,
            )
            await self._emit(__event_emitter__, "status", {"description": "✅ เสร็จ", "done": True})
            return response
        except httpx.ConnectTimeout:
            return "⚠️ ไม่สามารถเชื่อมต่อ AI Search ได้ — กรุณาลองใหม่ (timeout)"
        except httpx.HTTPStatusError as e:
            return f"⚠️ Search error (HTTP {e.response.status_code})"
        except Exception as e:
            return f"⚠️ เกิดข้อผิดพลาด: {str(e)[:300]}"

    async def _retrieve(self, query: str, search_key: str) -> dict:
        """Corporate docs only."""
        url = (
            f"{self.valves.search_endpoint}/knowledgebases('{self.valves.kb_name}')"
            f"/retrieve?api-version=2026-04-01"
        )
        async with httpx.AsyncClient(timeout=self.valves.search_timeout) as client:
            resp = await client.post(url, json={
                "intents": [{"search": query, "type": "semantic"}],
                "knowledgeSourceParams": [
                    {"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}
                ],
                "maxOutputSizeInTokens": max(self.valves.max_output_tokens, 5000),
            }, headers={"Content-Type": "application/json", "api-key": search_key})
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
                        for doc in results[:5]:
                            title = doc.get("title", "Untitled")
                            content = doc.get("content", "")[:500]
                            docs.append(f"[{title}]\n{content}")
                except (json.JSONDecodeError, TypeError):
                    pass
        return {"docs": docs}

    async def _generate(
        self, user_query: str, search_results: dict,
        message_history: list, openai_key: str,
    ) -> str:
        context = "\n\n".join(search_results["docs"]) if search_results["docs"] else "ไม่พบเอกสาร"
        has_docs = len(search_results.get("docs", [])) > 0

        source_hint = "ด้านล่างนี้คือเอกสารด้าน IT/องค์กรที่เกี่ยวข้อง:" if has_docs else (
            "⚠️ ไม่พบเอกสารที่เกี่ยวข้อง — ตอบตามความรู้ทั่วไป แต่แจ้งผู้ใช้"
        )

        system_prompt = f"""คุณคือ **ผู้ช่วยด้าน IT และองค์กร ของบริษัท หาดทิพย์ จำกัด (มหาชน)**

{source_hint}

{context}

## คำแนะนำ
- ตอบเป็นภาษาไทย ยกเว้นศัพท์เทคนิค
- ยึดเนื้อหาจากเอกสาร อ้างอิง [ชื่อเอกสาร] ทุกครั้ง
- ถ้าเป็นขั้นตอน → สรุปเป็นข้อๆ
- เอกสารครอบคลุม: MFA, VPN, Email O365, ห้องประชุม, IT Policy
- หากไม่มีข้อมูลเพียงพอ → บอกตามตรง"""

        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in message_history[-6:]:
            llm_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        url = (
            f"{self.valves.azure_endpoint}/openai/deployments/"
            f"{self.valves.deployment_name}/chat/completions?api-version={self.valves.api_version}"
        )
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(url, json={
                "messages": llm_messages, "temperature": 0.3,
                "max_completion_tokens": 4096, "stream": False,
            }, headers={"Content-Type": "application/json", "api-key": openai_key})
            resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def _emit(self, emitter: Any, event_type: str, data: dict):
        if emitter and hasattr(emitter, "__call__"):
            await emitter({"type": event_type, "data": data})

    async def get_models(self) -> list[dict]:
        return [{"id": "haadthip-corporate-knowledge", "name": "Haadthip Corporate Knowledge (Pipe)"}]
