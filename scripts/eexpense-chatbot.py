#!/usr/bin/env python3
"""
eexpense-chatbot.py — E-Expense Chatbot Engine (FAQ Search + State Machine)
============================================================================

Hybrid architecture:
  - FAQ Index (Azure AI Search): Direct Q&A via hybrid search (BM25 + vector + semantic)
  - State Machine: Manages multi-turn conversation when conditions are needed

Flow:
  User asks → Search FAQ index
    → Exact match (no conditions)? → Return answer directly
    → Multiple condition-variants found? → Ask clarifying question (buttons)
    → No good match? → Return best effort + suggestions

Usage:
  from eexpense_chatbot import EExpenseChatbot
  bot = EExpenseChatbot()
  answer = bot.ask("ขอล่วงหน้ากี่วัน")  # returns {"answer": "...", "choices": null}
  answer = bot.ask("มี")                # continues state, returns specific answer
"""

import os, json, hashlib
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

import requests
from openai import AzureOpenAI

# ── Config ──────────────────────────────────────────────
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT",
                             "https://srch-entchat-poc-sand.search.windows.net")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
INDEX_NAME = os.getenv("EEXPENSE_INDEX", "eexpense-faq-idx")
API_VERSION = "2024-07-01"

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT",
                             "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072

# ── Quick lookup map for common questions (no embedding needed) ──
QUICK_MAP = {
    "e-expense คืออะไร": "ANS26",
    "e-expense ใช้ทำอะไร": "ANS26",
    "ระบบ e-expense": "ANS26",
    "ค่าใช้จ่ายอะไรบ้าง": "ANS27",
    "รองรับค่าใช้จ่าย": "ANS27",
    "ประเภทค่าใช้จ่าย": "ANS27",
    "ไฟล์แนบ": "ANS31",
    "ขนาดไฟล์": "ANS32",
    "ไฟล์แนบขนาด": "ANS32",
    "ใครเป็นผู้อนุมัติ": "ANS9",
    "approver": "ANS9",
    "สายอนุมัติ": "ANS9",
    "ตั้ง delegate": "ANS10",
    "มอบอำนาจ": "ANS10",
    "ผู้รับมอบอำนาจ": "ANS10",
    "cost center": "ANS29",
    "cost center ไม่ถูกต้อง": "ANS11",
    "cost center แก้ไข": "ANS11",
    "ทำแทน": "ANS28",
    "ทำเอกสารแทน": "ANS28",
    "ผู้ร่วมเดินทาง": "ANS30",
    "requestor": "ANS30",
    "ดูประวัติ": "ANS18",
    "history": "ANS18",
    "เอกสารย้อนหลัง": "ANS18",
    "one day trip": "ANS5",
    "เช้าเย็นกลับ": "ANS5",
    "one-day": "ANS5",
    "โรงแรมอาหารเช้า": "ANS21",
    "หักค่าอาหาร": "ANS21",
    "วันหยุดค่าอาหาร": "ANS22",
    "เสาร์อาทิตย์": "ANS22",
    "ใบเสร็จค่าอาหาร": "ANS23",
    "แยกใบเสร็จ": "ANS23",
    "แอดมินเคลียร์": "ANS24",
    "ค่าอาหารเกิน": "ANS25",
    "เบิกเพิ่มส่วนต่าง": "ANS25",
    "out source": "ANS8",
    "สัญญาจ้าง": "ANS8",
    "ค่าอาหารคำนวณ": "ANS33",
}


@dataclass
class ConversationState:
    """Track multi-turn conversation context."""
    session_id: str
    history: list = field(default_factory=list)
    pending_conditions: dict = field(default_factory=dict)  # {ans_id: [missing_conditions]}
    last_question_id: Optional[str] = None
    resolved_conditions: list = field(default_factory=list)  # conditions already resolved


class EExpenseChatbot:
    """E-Expense FAQ Chatbot with hybrid search + state machine."""

    def __init__(self):
        self._openai_client = None
        self._sessions: dict[str, ConversationState] = {}

    # ── Public API ──────────────────────────────────────

    def ask(self, user_message: str, session_id: str = "default") -> dict:
        """Process a user message and return a response.

        Returns:
            {"type": "answer"|"clarify"|"fallback",
             "text": str,
             "choices": [{"label": "...", "value": "..."}] | None,
             "sourceId": str | None}
        """
        state = self._get_session(session_id)
        state.history.append({"role": "user", "content": user_message})

        # Step 1: Quick keyword lookup
        quick_hit = self._quick_lookup(user_message)
        if quick_hit:
            result = self._resolve_answer(quick_hit, state)
            if result:
                state.history.append({"role": "bot", "content": result["text"]})
                return result

        # Step 2: Hybrid search (BM25 + vector + semantic)
        search_results = self._hybrid_search(user_message, top=8)

        if not search_results:
            fallback = self._fallback_response(user_message)
            state.history.append({"role": "bot", "content": fallback["text"]})
            return fallback

        # Step 3: Analyze results
        # Group by answer (deduplicate different paths to same answer)
        answer_groups = defaultdict(list)
        for doc in search_results:
            answer_groups[doc.get("sourceId")].append(doc)

        # If only one unique answer, return it
        if len(answer_groups) == 1:
            ans_id = list(answer_groups.keys())[0]
            doc = answer_groups[ans_id][0]
            result = self._format_answer(doc)
            state.history.append({"role": "bot", "content": result["text"]})
            return result

        # If multiple answers, check if they differ only by conditions
        # If so, ask user to clarify
        clarifying = self._build_clarification(answer_groups, state)
        if clarifying:
            state.pending_conditions = clarifying["pending"]
            state.history.append({"role": "bot", "content": clarifying["text"]})
            return clarifying

        # Otherwise, return top result
        doc = search_results[0]
        result = self._format_answer(doc)
        state.history.append({"role": "bot", "content": result["text"]})
        return result

    def reset_session(self, session_id: str = "default"):
        self._sessions.pop(session_id, None)

    # ── Internal Methods ────────────────────────────────

    def _get_session(self, session_id: str) -> ConversationState:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationState(session_id=session_id)
        return self._sessions[session_id]

    def _get_openai_client(self) -> AzureOpenAI:
        if self._openai_client is None and OPENAI_KEY:
            self._openai_client = AzureOpenAI(
                api_key=OPENAI_KEY,
                api_version="2024-12-01-preview",
                azure_endpoint=OPENAI_ENDPOINT,
            )
        return self._openai_client

    def _quick_lookup(self, query: str) -> Optional[str]:
        """Fast keyword lookup to avoid embedding call for common questions."""
        q = query.lower().strip()
        # Direct match
        if q in QUICK_MAP:
            return QUICK_MAP[q]
        # Partial match (longest keyword first)
        for keyword, ans_id in sorted(QUICK_MAP.items(), key=lambda x: -len(x[0])):
            if keyword in q:
                return ans_id
        return None

    def _resolve_answer(self, ans_id: str, state: ConversationState) -> Optional[dict]:
        """Resolve an answer by ID, fetching from search if needed."""
        # Try to find exact document
        url = (f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/search"
               f"?api-version={API_VERSION}")
        payload = {
            "search": f"*",
            "filter": f"sourceId eq '{ans_id}'",
            "top": 10,
            "select": "id,question,answer,shortAnswer,category,conditions,sourceId,choiceType",
        }
        headers = {"api-key": SEARCH_KEY, "Content-Type": "application/json"}
        try:
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                docs = resp.json().get("value", [])
                if docs:
                    # If only one variant, return it
                    if len(docs) == 1:
                        return self._format_answer(docs[0])
                    # Multiple variants (different conditions) — ask user
                    return self._ask_condition(docs, state)
        except Exception:
            pass
        return None

    def _hybrid_search(self, query: str, top: int = 8) -> list[dict]:
        """Hybrid search: BM25 + vector + semantic ranking."""
        url = (f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/search"
               f"?api-version={API_VERSION}")

        payload = {
            "search": query,
            "top": top,
            "queryType": "semantic",
            "semanticConfiguration": "eexpense-semantic-config",
            "select": "id,question,answer,shortAnswer,category,conditions,sourceId,choiceType,contextQuestions",
        }

        # Add vector search if OpenAI client available
        client = self._get_openai_client()
        if client:
            try:
                emb_resp = client.embeddings.create(
                    model=EMBEDDING_DEPLOYMENT,
                    input=[query],
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                vector = emb_resp.data[0].embedding
                payload["vectorQueries"] = [{
                    "vector": vector,
                    "fields": "contentVector",
                    "kind": "vector",
                    "k": top,
                }]
            except Exception:
                pass  # Fall back to text-only search

        headers = {"api-key": SEARCH_KEY, "Content-Type": "application/json"}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("value", [])
            # Fallback: retry without semantic
            if resp.status_code == 400:
                payload.pop("queryType", None)
                payload.pop("semanticConfiguration", None)
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 200:
                    return resp.json().get("value", [])
        except Exception:
            pass
        return []

    def _format_answer(self, doc: dict) -> dict:
        """Format a search document into a chatbot response."""
        answer = doc.get("answer", "")
        short = doc.get("shortAnswer", answer[:150])
        question = doc.get("question", "")
        conditions = doc.get("conditions", [])

        text = answer
        if conditions:
            cond_text = ", ".join(conditions)
            text += f"\n\n📌 *เงื่อนไข: {cond_text}*"

        return {
            "type": "answer",
            "text": text,
            "choices": None,
            "sourceId": doc.get("sourceId"),
            "question": question,
            "shortAnswer": short,
            "category": doc.get("category"),
        }

    def _ask_condition(self, docs: list[dict], state: ConversationState) -> dict:
        """Build a clarification question when multiple condition-variants exist."""
        # Extract unique condition questions
        cond_map = {}  # {condition_label: next_docs}
        for doc in docs:
            conditions = doc.get("conditions") or []
            for c in conditions:
                # "มีขอทดรองจ่ายหรือไม่? → A : มี" → label="A : มี", q="มีขอทดรองจ่ายหรือไม่?"
                if " → " in c:
                    q_part, a_part = c.split(" → ", 1)
                    key = a_part.strip()
                    if key not in cond_map:
                        cond_map[key] = []
                    cond_map[key].append(doc)

        if len(cond_map) <= 1:
            return self._format_answer(docs[0])

        choices = []
        pending = {}
        for label, matching_docs in cond_map.items():
            # Find the question that leads to this choice
            source_ids = list(set(d.get("sourceId") for d in matching_docs))
            choices.append({"label": label, "value": label})
            pending[label] = source_ids

        text = "กรุณาเลือกเงื่อนไขเพิ่มเติมเพื่อให้ได้คำตอบที่ถูกต้อง:"

        return {
            "type": "clarify",
            "text": text,
            "choices": choices,
            "sourceId": None,
            "pending": pending,
        }

    def _build_clarification(self, answer_groups: dict, state: ConversationState) -> Optional[dict]:
        """Build a clarification question when multiple answer groups exist."""
        # Flatten all docs
        all_docs = []
        for docs in answer_groups.values():
            all_docs.extend(docs)

        # Find common condition questions
        cond_count = defaultdict(set)
        for doc in all_docs:
            conditions = doc.get("conditions") or []
            for c in conditions:
                if " → " in c:
                    q_part, _ = c.split(" → ", 1)
                    cond_count[q_part.strip()].add(doc.get("sourceId"))

        if len(cond_count) == 0:
            return None  # Can't clarify

        # Pick the most discriminating condition question
        best_q = max(cond_count.keys(), key=lambda k: len(cond_count[k]))
        unique_choices = set()
        for doc in all_docs:
            for c in (doc.get("conditions") or []):
                if best_q in c and " → " in c:
                    _, a_part = c.split(" → ", 1)
                    unique_choices.add(a_part.strip())

        if len(unique_choices) <= 1:
            return None

        choices = [{"label": ch, "value": ch} for ch in sorted(unique_choices)]
        text = f"{best_q}?"

        pending = {}
        for ch in unique_choices:
            pending[ch] = [d.get("sourceId") for d in all_docs
                           if any(ch in c for c in (d.get("conditions") or []))]

        return {
            "type": "clarify",
            "text": text,
            "choices": choices,
            "sourceId": None,
            "pending": pending,
        }

    def _fallback_response(self, query: str) -> dict:
        return {
            "type": "fallback",
            "text": (
                "ขออภัยค่ะ ฉันยังไม่มีข้อมูลเกี่ยวกับคำถามนี้ในระบบ E-Expense "
                "กรุณาลองถามคำถามอื่น หรือติดต่อ IT Service โครงการ E-Expense เพื่อสอบถามเพิ่มเติมค่ะ"
            ),
            "choices": None,
            "sourceId": None,
        }


# ── Demo CLI ───────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if not SEARCH_KEY:
        print("❌ Set AZURE_SEARCH_KEY environment variable")
        sys.exit(1)

    bot = EExpenseChatbot()
    session_id = "demo"
    print("=" * 60)
    print(" 🤖 E-Expense Chatbot (FAQ + State Machine)")
    print("   Type 'reset' to clear session, 'quit' to exit")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Bye!")
            break
        if user_input.lower() == "reset":
            bot.reset_session(session_id)
            print("🔄 Session reset")
            continue

        result = bot.ask(user_input, session_id)

        prefix = {"answer": "🤖", "clarify": "🤔", "fallback": "⚠️"}
        emoji = prefix.get(result["type"], "💬")
        print(f"\n{emoji} Bot: {result['text']}")

        if result.get("choices"):
            print("   ┌─ ตัวเลือก ─────────────")
            for i, ch in enumerate(result["choices"], 1):
                print(f"   │ {i}. {ch['label']}")
            print("   └────────────────────────")
            print("   (พิมพ์หมายเลขหรือข้อความที่ต้องการ)")

        if result.get("sourceId"):
            print(f"   📎 แหล่งที่มา: {result['sourceId']} | {result.get('category', '')}")
