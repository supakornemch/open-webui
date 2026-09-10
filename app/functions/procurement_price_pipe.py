"""
title: Procurement Price Assistant API
author: Haadthip DIO
version: 1.2
required_open_webui_version: 0.5.0
"""
import json
import os
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import OpenAI
from pydantic import BaseModel, Field

FIELDS = [
    "logical_item_id", "year", "category", "product_name", "product_aliases",
    "product_type", "product_spec_text", "product_condition_text", "pricing_basis",
    "notes_text", "award_vendors", "price_min", "price_max", "quantity_min_all",
    "quantity_max_all", "tiers",
]
CATEGORIES = ["POSM", "Printing-MKT", "Printing-Rate", "Garment", "Premium"]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_procurement_prices",
            "description": "Search awarded procurement prices from the procurement catalog.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "year": {"type": "integer"},
                    "min_price": {"type": "number"},
                    "max_price": {"type": "number"},
                    "quantity": {"type": "integer"},
                    "use_semantic": {"type": "boolean"},
                    "sort_by_price": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_total_price",
            "description": (
                "MANDATORY after search when the user supplies a quantity. "
                "Selects the exact awarded tier and calculates total price deterministically. "
                "Copy tiers verbatim from the chosen search result; never calculate mentally."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "quantity": {"type": "integer", "minimum": 1},
                    "tiers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "quantity_label": {"type": ["string", "null"]},
                                "quantity_min": {"type": "integer"},
                                "quantity_max": {"type": ["integer", "null"]},
                                "awarded_price": {"type": "number"},
                            },
                            "required": ["quantity_min", "awarded_price"],
                        },
                    },
                },
                "required": ["quantity", "tiers"],
            },
        },
    },
]


class Pipe:
    class Valves(BaseModel):
        AZURE_SEARCH_ENDPOINT: str = Field(default="")
        AZURE_SEARCH_KEY: str = Field(default="")
        AZURE_SEARCH_INDEX: str = Field(default="procurement-catalog-v1")
        AZURE_SEARCH_API_VERSION: str = Field(default="2024-07-01")
        AZURE_SEARCH_SEMANTIC_CONFIG: str = Field(default="procurement-semantic")
        LLM_BASE_URL: str = Field(default="")
        LLM_API_KEY: str = Field(default="")
        LLM_MODEL: str = Field(default="deploy-gpt-5.4-nano")
        EMBEDDING_MODEL: str = Field(default="deploy-embedding-3-large")
        MAX_TOOL_ROUNDS: int = Field(default=4)
        MAX_RESULTS: int = Field(default=5)

    def __init__(self):
        self.valves = self.Valves()
        v = self.valves
        # valves carry admin config (set via UI/DB); env is fallback for fresh deploys
        if not v.AZURE_SEARCH_ENDPOINT:
            v.AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        if not v.AZURE_SEARCH_KEY:
            v.AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
        if not v.LLM_BASE_URL:
            base = os.getenv("OPENAI_API_BASE_URL", "").rstrip("/")
            v.LLM_BASE_URL = base[:-3] if base.endswith("/v1") else base
        if not v.LLM_API_KEY:
            v.LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")

    def _embedding(self, text: str) -> list[float]:
        client = OpenAI(api_key=self.valves.LLM_API_KEY,
                        base_url=self.valves.LLM_BASE_URL.rstrip("/") + "/v1")
        return client.embeddings.create(input=text, model=self.valves.EMBEDDING_MODEL).data[0].embedding

    def _filter(self, args: dict, include_quantity: bool = True) -> Optional[str]:
        f = []
        if args.get("category"):
            f.append(f"category eq '{args['category']}'")
        if args.get("year"):
            f.append(f"year eq {args['year']}")
        if args.get("min_price") is not None:
            f.append(f"price_min ge {args['min_price']}")
        if args.get("max_price") is not None:
            f.append(f"price_max le {args['max_price']}")
        if include_quantity and args.get("quantity") is not None:
            q = args["quantity"]
            f.append(f"tiers/any(t: t/quantity_min le {q} and (t/quantity_max ge {q} or t/quantity_max eq null))")
        return " and ".join(f) or None

    def _search(self, args: dict, include_quantity: bool = True) -> list[dict]:
        client = SearchClient(endpoint=self.valves.AZURE_SEARCH_ENDPOINT,
                              index_name=self.valves.AZURE_SEARCH_INDEX,
                              credential=AzureKeyCredential(self.valves.AZURE_SEARCH_KEY),
                              api_version=self.valves.AZURE_SEARCH_API_VERSION)
        kwargs = {
            "search_text": args["query"],
            "search_mode": "any",
            "vector_queries": [VectorizedQuery(vector=self._embedding(args["query"]), k_nearest_neighbors=50, fields="content_vector")],
            "filter": self._filter(args, include_quantity),
            "top": min(self.valves.MAX_RESULTS, 5),
            "select": FIELDS,
        }
        if args.get("use_semantic"):
            kwargs["query_type"] = "semantic"
            kwargs["semantic_configuration_name"] = self.valves.AZURE_SEARCH_SEMANTIC_CONFIG
        results = list(client.search(**kwargs))
        if not results and args.get("category"):
            args = dict(args)
            args.pop("category", None)
            results = self._search(args, include_quantity)
        if not results and include_quantity and args.get("quantity") is not None:
            results = self._search(args, False)
        if args.get("sort_by_price"):
            results.sort(key=lambda x: x.get("price_min") if x.get("price_min") is not None else float("inf"))
        return results

    def _tool(self, args: dict) -> str:
        rows = []
        for r in self._search(dict(args)):
            rows.append({k: r.get(k) for k in FIELDS if k != "content_vector"})
        return json.dumps({"success": True, "query": args.get("query"), "total_results": len(rows), "results": rows}, ensure_ascii=False)

    def _calculate_total_price(self, args: dict) -> str:
        quantity = args.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            return json.dumps({"success": False, "reason": "invalid_quantity", "error": "quantity must be a positive integer"})

        valid = [
            t for t in (args.get("tiers") or [])
            if isinstance(t, dict)
            and isinstance(t.get("quantity_min"), int)
            and isinstance(t.get("awarded_price"), (int, float))
        ]
        if not valid:
            return json.dumps({"success": False, "reason": "invalid_tiers", "error": "No usable awarded-price tier"})
        valid.sort(key=lambda tier: tier["quantity_min"])

        matched = next(
            (
                tier for tier in valid
                if tier["quantity_min"] <= quantity
                and (tier.get("quantity_max") is None or quantity <= tier["quantity_max"])
            ),
            None,
        )
        if matched is None and quantity < valid[0]["quantity_min"]:
            lowest = valid[0]
            moq = lowest["quantity_min"]
            unit = lowest["awarded_price"]
            return json.dumps({
                "success": True,
                "quantity": quantity,
                "below_moq": True,
                "moq": moq,
                "unit_price_at_moq": unit,
                "total_at_moq": round(unit * moq, 2),
            }, ensure_ascii=False)
        if matched is None:
            return json.dumps({
                "success": False,
                "reason": "no_matching_tier",
                "quantity": quantity,
                "error": "No awarded tier covers this quantity; do not extrapolate a price",
            }, ensure_ascii=False)

        unit = matched["awarded_price"]
        total = round(unit * quantity, 2)
        return json.dumps({
            "success": True,
            "quantity": quantity,
            "matched_tier": {
                "quantity_label": matched.get("quantity_label"),
                "quantity_min": matched["quantity_min"],
                "quantity_max": matched.get("quantity_max"),
            },
            "unit_price": unit,
            "total_price": total,
            "formula": f"{unit} x {quantity} = {total}",
        }, ensure_ascii=False)

    def _dispatch_tool(self, name: str, args: dict) -> str:
        if name == "search_procurement_prices":
            return self._tool(args)
        if name == "calculate_total_price":
            return self._calculate_total_price(args)
        return json.dumps({"success": False, "error": f"unknown tool: {name}"})

    def pipe(self, body: dict, __user__: dict = None, __event_emitter__=None) -> str:
        messages = list(body.get("messages") or [])
        system = body.get("system")
        if system:
            messages.insert(0, {"role": "system", "content": system})
        client = OpenAI(api_key=self.valves.LLM_API_KEY,
                        base_url=self.valves.LLM_BASE_URL.rstrip("/") + "/v1")
        for _ in range(max(1, min(self.valves.MAX_TOOL_ROUNDS, 6))):
            response = client.chat.completions.create(
                model=self.valves.LLM_MODEL, messages=messages, tools=TOOLS,
                tool_choice="auto", extra_body={"prompt_cache_key": "procurement_ai"},
            )
            choice = response.choices[0]
            msg = choice.message
            if choice.finish_reason != "tool_calls" or not msg.tool_calls:
                return msg.content or ""
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": [x.model_dump() for x in msg.tool_calls]})
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = self._dispatch_tool(call.function.name, args)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        return "ขออภัยครับ ระบบค้นหาใช้เวลานานเกินกำหนด กรุณาลองใหม่อีกครั้ง"
