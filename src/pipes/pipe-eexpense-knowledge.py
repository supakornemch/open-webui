"""
title: Haadthip E-Expense Knowledge (Pipe)
author: Haadthip
version: 1.0
required_open_webui_version: 0.1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Pipe — E-Expense FAQ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Direct search on eexpense-faq-idx (hybrid: BM25 + vector + semantic).
Not via Knowledge Base — uses direct /docs/search endpoint.

Install in Open WebUI:
  Admin Settings → Functions → + → paste this file → Save
  Then select "Haadthip E-Expense Knowledge (Pipe)" as the model
"""

import json
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
        )
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
        )
        index_name: str = Field(default="eexpense-faq-idx")
        max_results: int = Field(default=5, ge=1, le=10)
        search_timeout: int = Field(default=30)
        azure_endpoint: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
        )
        azure_api_key: str = Field(
            default=os.environ.get("OPENAI_API_KEY", ""),
        )
        deployment_name: str = Field(default="deploy-gpt-5.4")
        api_version: str = Field(default="2024-12-01-preview")

    def __init__(self):
        self.type = "pipe"
        self.id = "haadthip-eexpense-knowledge"
        self.name = "Haadthip E-Expense Knowledge (Pipe)"
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
            "description": "🔍 กำลังค้นหาจาก FAQ E-Expense...", "done": False
        })

        try:
            search_results = await self._retrieve(query=last_user_msg, search_key=search_key)
            found = len(search_results.get("docs", []))
            await self._emit(__event_emitter__, "status", {
                "description": f"📄 พบ {found} คำถาม-คำตอบ → กำลังสรุป...", "done": False
            })
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
        """Direct index search (hybrid) — not via KB."""
        url = (
            f"{self.valves.search_endpoint}/indexes/{self.valves.index_name}"
            f"/docs/search?api-version=2024-07-01"
        )
        async with httpx.AsyncClient(timeout=self.valves.search_timeout) as client:
            resp = await client.post(url, json={
                "search": query,
                "queryType": "semantic",
                "semanticConfiguration": "eexpense-semantic-config",
                "top": self.valves.max_results,
                "select": "question,answer,category,keywords",
                "searchFields": "question,answer,keywords",
            }, headers={"Content-Type": "application/json", "api-key": search_key})
            resp.raise_for_status()
            data = resp.json()

        docs = []
        for doc in data.get("value", []):
            question = doc.get("question", "?")
            answer = doc.get("answer", "")
            category = doc.get("category", "")
            docs.append(f"[{category}] {question}\n{answer[:500]}")
        return {"docs": docs}

    async def _generate(
        self, user_query: str, search_results: dict,
        message_history: list, openai_key: str,
    ) -> str:
        context = "\n\n".join(search_results["docs"]) if search_results["docs"] else "ไม่พบคำตอบ"
        has_docs = len(search_results.get("docs", [])) > 0

        source_hint = "ด้านล่างนี้คือคำถาม-คำตอบจาก FAQ E-Expense:" if has_docs else (
            "⚠️ ไม่พบคำตอบที่เกี่ยวข้อง — แจ้งผู้ใช้ให้ติดต่อฝ่ายบัญชี/การเงิน"
        )

        system_prompt = f"""คุณคือ **ผู้ช่วยด้าน E-Expense ของบริษัท หาดทิพย์ จำกัด (มหาชน)**

E-Expense คือระบบค่าใช้จ่ายพนักงาน: ขอแผนการเดินทาง, เบิกทดรองจ่าย, เคลียร์ค่าใช้จ่าย, ค่ารักษาพยาบาล

{source_hint}

{context}

## คำแนะนำ
- ตอบเป็นภาษาไทย
- ยึดเนื้อหาจาก FAQ E-Expense — ระบุเงื่อนไขให้ครบ (Level, Cost Center, วันที่)
- ตอบให้กระชับ ตรงประเด็น
- ถ้ามีหลายกรณี → แยกเป็นข้อย่อย
- หากไม่มีข้อมูลเพียงพอ → แนะนำให้ติดต่อฝ่ายบัญชี/การเงิน"""

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
        return [{"id": "haadthip-eexpense-knowledge", "name": "Haadthip E-Expense Knowledge (Pipe)"}]
