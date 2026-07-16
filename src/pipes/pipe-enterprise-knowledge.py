"""
title: Genie — Enterprise Knowledge (Pipe)
author: Haadthip DIO
version: 1.0
required_open_webui_version: 0.1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open WebUI Pipe — Enterprise Document Q&A
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Answers questions using enterprise-docs-idx (Azure AI Search).
Combines internal docs + HR policies + Open WebUI help docs.

How it works:
  1. User asks a question
  2. Pipe searches enterprise-docs-idx (hybrid: BM25 + vector + semantic)
  3. Pipe passes search results as context to GPT-5.4
  4. Response includes citations, document names, and Thai-friendly answers

Setup:
  Admin → Functions → + → paste → Save
  Workspace → Models → select "Genie — Enterprise Knowledge (Pipe)"

Recommended Agent Configuration:
  - Model: Genie — Enterprise Knowledge (Pipe)
  - Knowledge: enterprise-docs-idx (via tools or direct)
  - System Prompt: Thai-friendly enterprise assistant
"""

import asyncio
import json
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field
from openai import AsyncAzureOpenAI


class Pipe:
    class Valves(BaseModel):
        # ── Search ──
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
            description="Search index",
        )
        max_results: int = Field(
            default=5, description="Max search results",
        )

        # ── LLM ──
        azure_endpoint: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
            description="AOAI endpoint",
        )
        azure_api_key: str = Field(
            default=os.environ.get("OPENAI_API_KEY", ""),
            description="AOAI key",
        )
        deployment_name: str = Field(
            default="deploy-gpt-5.4",
            description="LLM deployment for answer generation",
        )
        max_tokens: int = Field(
            default=2000, description="Max answer tokens",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.name = "Genie — Enterprise Knowledge"
        self.client = None

    async def pipe(self, body: dict, __user__: dict = None, __event_emitter__=None):
        """
        Called for each user message. Returns assistant reply.
        """
        messages = body.get("messages", [])
        user_message = messages[-1]["content"] if messages else ""

        if not user_message.strip():
            return "Please ask a question about Haadthip documents or systems."

        # ── 1. Search ──
        search_key = self.valves.search_api_key or os.environ.get(
            "AZURE_SEARCH_ADMIN_KEY", ""
        )
        context = await self._search(user_message, search_key)

        # ── 2. Build system prompt with context ──
        system_prompt = f"""You are Genie, Haadthip's enterprise AI assistant.
Answer questions using the provided document excerpts. Follow these rules:

1. **Answer from documents** — base your answer on the provided context.
2. **Cite sources** — mention document names in your answer (e.g., "ตามระเบียบ...", "ตามคู่มือ...").
3. **Thai-friendly** — answer in the same language as the question (Thai or English).
4. **Be specific** — give concrete steps, dates, amounts when available.
5. **Acknowledge gaps** — if the documents don't cover the question, say so honestly.

## Document Excerpts
{context}

## Current User
{__user__.get('name', 'Unknown') if __user__ else 'Unknown'}"""

        # ── 3. Generate answer ──
        if not self.client:
            self.client = AsyncAzureOpenAI(
                api_key=self.valves.azure_api_key or os.environ.get("OPENAI_API_KEY", ""),
                azure_endpoint=self.valves.azure_endpoint,
                api_version="2024-10-21",
            )

        try:
            resp = await self.client.chat.completions.create(
                model=self.valves.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_completion_tokens=self.valves.max_tokens,
                temperature=0.3,
            )
            answer = resp.choices[0].message.content
            return answer
        except Exception as e:
            # Fallback: just return the search results
            return f"⚠️ LLM error: {e}\n\n## Search Results\n{context}"

    async def _search(self, query: str, key: str) -> str:
        """Search enterprise-docs-idx with semantic ranking."""
        if not key:
            return "[No search key configured]"

        url = (
            f"{self.valves.search_endpoint}/indexes/{self.valves.index_name}"
            f"/docs/search?api-version=2024-07-01"
        )

        body = {
            "search": query,
            "queryType": "semantic",
            "semanticConfiguration": "semantic-config",
            "searchFields": "content,summary,file_name,category",
            "select": "file_name,corpus,category,content,summary",
            "top": self.valves.max_results,
            "answers": "extractive|count-1",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    url, json=body,
                    headers={"Content-Type": "application/json", "api-key": key},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                return f"[Search error: {e}]"

        chunks = []
        for doc in data.get("value", []):
            corpus = doc.get("corpus", "?")
            category = doc.get("category", "")
            fname = doc.get("file_name", "Untitled")
            content = doc.get("content", "")[:600]
            summary = doc.get("summary", "")
            chunks.append(
                f"📄 [{corpus}/{category}] {fname}\n"
                f"   {summary}\n"
                f"   {content}\n"
            )

        # Prepend semantic answer if available
        if data.get("@search.answers"):
            answer = data["@search.answers"][0].get("text", "")
            chunks.insert(0, f"📝 **Extracted Answer:** {answer}\n")

        return "\n".join(chunks) if chunks else "[No documents found]"
