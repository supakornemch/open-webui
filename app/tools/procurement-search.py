"""
title: Procurement Price Search
author: Haadthip DIO
version: 3.1
required_open_webui_version: 0.5.0

Search procurement prices from Azure AI Search index procurement-catalog-v1.
One document = one logical product with tiered pricing. Prices come from the
Excel Master verbatim. This tool never computes or invents prices.

Capabilities:
- Hybrid search: BM25 keyword + vector (3072-dim), fused by Azure RRF
- Thai word segmentation via th.microsoft analyzer
- Semantic rerank on top (optional, queryType=semantic)
- Filter: year, category, price range, quantity tier
- Quantity tier matching: tiers/any OData filter
- Category fallback: drops category filter if no results found

Category guide (send ONLY when user explicitly names the category):
- POSM — สื่อ ณ จุดขาย (ร่มโค้ก, ถังน้ำแข็ง, กล่องทิชชู, PM Rack, Mega Rack, ป้าย)
- Printing-MKT — งานพิมพ์การตลาด (โคมไฟ, PP Board, แบนเนอร์, ผ้าปูโต๊ะ, สติ๊กเกอร์, ธงราว)
- Printing-Rate — งานพิมพ์ตามเรท (Arch, Wrap Around, โปสเตอร์, Tent card, Wobbler, ธงปีกนก, Sticker PVC, Coupon)
- Garment — เสื้อผ้า (เสื้อยืด, เสื้อโปโล, เสื้อแจ็คเก็ต, สกรีน, ค่าปัก)
- Premium — ของพรีเมียม (ร่ม, แก้วกระดาษ, ผ้าเบอร์วิ่ง, Menu Stand, เก้าอี้)

Quantity filter warning: products have a minimum order quantity (MOQ).
A quantity filter removes products whose MOQ exceeds the request. Search
WITHOUT quantity first to identify the product, then check its tiers for
the user's requested quantity. If the quantity is below MOQ, report the
MOQ and ask whether the user wants to adjust.

Authorization: Available to all users with access to the model.
"""

import json
import os
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from fastapi import Request
from openai import OpenAI
from pydantic import BaseModel, Field

_SELECT_FIELDS = [
    "logical_item_id",
    "year",
    "category",
    "product_name",
    "product_aliases",
    "product_type",
    "product_spec_text",
    "product_condition_text",
    "pricing_basis",
    "notes_text",
    "award_vendors",
    "price_min",
    "price_max",
    "quantity_min_all",
    "quantity_max_all",
    "tiers",
]


class Tools:
    class Valves(BaseModel):
        AZURE_SEARCH_ENDPOINT: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
            description="Azure AI Search endpoint"
        )
        AZURE_SEARCH_KEY: str = Field(
            default="",
            description="Azure AI Search admin key"
        )
        AZURE_SEARCH_INDEX: str = Field(
            default="procurement-catalog-v1",
            description="Search index name"
        )
        AZURE_SEARCH_SEMANTIC_CONFIG: str = Field(
            default="procurement-semantic",
            description="Semantic configuration name (for semantic mode)"
        )
        AZURE_OPENAI_ENDPOINT: str = Field(
            default="https://app-litellm-poc-sand.azurewebsites.net",
            description="OpenAI-compatible endpoint for embeddings (LiteLLM proxy base URL, no /v1 suffix)"
        )
        AZURE_OPENAI_KEY: str = Field(
            default="",
            description="Azure OpenAI API key"
        )
        AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = Field(
            default="deploy-embedding-3-large",
            description="Embedding model deployment name"
        )
        AZURE_OPENAI_API_VERSION: str = Field(
            default="2024-10-21",
            description="Azure OpenAI API version"
        )
        AZURE_SEARCH_API_VERSION: str = Field(
            default="2024-07-01",
            description="Azure AI Search API version"
        )
        max_results: int = Field(
            default=5,
            description="Maximum number of search results to return (capped at 5 per round)"
        )
        max_search_rounds: int = Field(
            default=3,
            description="Maximum search rounds per invocation (exact + wildcard retry)"
        )

    def __init__(self):
        self.valves = self.Valves()

        # Load from environment if not set in valves
        if not self.valves.AZURE_SEARCH_KEY:
            self.valves.AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
        if not self.valves.AZURE_OPENAI_KEY:
            self.valves.AZURE_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
        if self.valves.AZURE_OPENAI_ENDPOINT == "https://aif-entchat-poc-sand.cognitiveservices.azure.com":
            self.valves.AZURE_OPENAI_ENDPOINT = os.getenv(
                "OPENAI_API_BASE_URL", self.valves.AZURE_OPENAI_ENDPOINT
            )

    def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text using an OpenAI-compatible endpoint.

        The LiteLLM proxy exposes /v1/embeddings (OpenAI style) rather than
        Azure's /openai/deployments/... path, so we use the OpenAI client with
        base_url=<endpoint>/v1.
        """
        client = OpenAI(
            api_key=self.valves.AZURE_OPENAI_KEY,
            base_url=self.valves.AZURE_OPENAI_ENDPOINT.rstrip("/") + "/v1",
        )
        response = client.embeddings.create(
            input=text,
            model=self.valves.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        )
        return response.data[0].embedding

    def _build_filter(
        self,
        category: Optional[str] = None,
        year: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        quantity: Optional[int] = None,
    ) -> Optional[str]:
        """Build OData filter string against the product-level schema."""
        filters = []

        if category:
            filters.append(f"category eq '{category}'")
        if year:
            filters.append(f"year eq {year}")
        if min_price is not None:
            filters.append(f"price_min ge {min_price}")
        if max_price is not None:
            filters.append(f"price_max le {max_price}")
        if quantity is not None:
            # deterministic tier matching: a tier that can serve the quantity
            filters.append(
                f"tiers/any(t: t/quantity_min le {quantity} and "
                f"(t/quantity_max ge {quantity} or t/quantity_max eq null))"
            )

        return " and ".join(filters) if filters else None

    def _format_result(self, result: dict) -> dict:
        """Flatten a product document into a readable result.

        Tiers carry quantity + awarded_price. Values are returned verbatim
        from the index; nothing is computed. award_vendors (ผู้ผ่านการประมูล)
        comes from the รายชื่อผู้ผ่านการประมูล column.
        """
        tiers = []
        for tier in result.get("tiers") or []:
            tiers.append(
                {
                    "lead_time": tier.get("lead_time"),
                    "quantity_label": tier.get("quantity_label"),
                    "quantity_min": tier.get("quantity_min"),
                    "quantity_max": tier.get("quantity_max"),
                    "awarded_price": tier.get("awarded_price"),
                }
            )

        return {
            "logical_item_id": result.get("logical_item_id"),
            "year": result.get("year"),
            "category": result.get("category"),
            "product_name": result.get("product_name"),
            "product_aliases": result.get("product_aliases") or [],
            "product_type": result.get("product_type"),
            "pricing_basis": result.get("pricing_basis"),
            "product_spec_text": result.get("product_spec_text"),
            "product_condition_text": result.get("product_condition_text"),
            "notes_text": result.get("notes_text"),
            "award_vendors": result.get("award_vendors") or [],
            "price_min": result.get("price_min"),
            "price_max": result.get("price_max"),
            "quantity_min_all": result.get("quantity_min_all"),
            "quantity_max_all": result.get("quantity_max_all"),
            "tiers": tiers,
            "score": result.get("@search.score"),
        }

    def _search(
        self,
        search_text: str,
        query_vector: list[float],
        filter_expr: Optional[str],
        use_semantic: bool,
    ) -> list[dict]:
        """Run HYBRID search: BM25 full-text (search_text) + vector (query_vector).

        Azure AI Search fuses the two result sets (RRF) into a single ranked
        list. `search_mode="any"` keeps the full-text side permissive so Thai
        keyword hits and vector matches both contribute. Semantic reranking
        (when enabled) is applied ON TOP of the hybrid results.
        """
        client = SearchClient(
            endpoint=self.valves.AZURE_SEARCH_ENDPOINT,
            index_name=self.valves.AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(self.valves.AZURE_SEARCH_KEY),
            api_version=self.valves.AZURE_SEARCH_API_VERSION,
        )
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=50,
            fields="content_vector",
        )
        kwargs = {
            "search_text": search_text,
            "search_mode": "any",  # hybrid: BM25 + vector fused
            "vector_queries": [vector_query],
            "filter": filter_expr,
            "top": max(1, min(self.valves.max_results, 5)),  # cap: 5 items per round
            "select": _SELECT_FIELDS,
        }
        if use_semantic:
            kwargs["query_type"] = "semantic"
            kwargs["semantic_configuration_name"] = self.valves.AZURE_SEARCH_SEMANTIC_CONFIG
        return list(client.search(**kwargs))

    async def search_procurement_prices(
        self,
        query: str,
        category: Optional[str] = None,
        year: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        quantity: Optional[int] = None,
        use_semantic: bool = False,
        sort_by_price: bool = False,
        use_wildcard: bool = False,
        __user__: dict = None,
        __request__: Request = None,
        __event_emitter__=None,
    ) -> str:
        """
        Search procurement products. Hybrid retrieval: keyword + vector.

        Send quantity ONLY after identifying the product. Quantity filter
        removes products whose minimum order quantity exceeds the request.
        If you send quantity on the first search and get zero results,
        retry without quantity first to find the product, then check its
        tiers.

        Args:
            query: Search terms in Thai or English. Be specific. Include
                  size, color, material when available (e.g. "ร่มโค้ก 40 นิ้ว
                  โครงไฟเบอร์" not just "ร่ม").
            category: Send ONLY when user states the category explicitly.
                      Do NOT guess. Wrong category kills results.
            year: Filter by year. Default: search all years.
            min_price: Minimum awarded price.
            max_price: Maximum awarded price.
            quantity: DO NOT send on the first search. Send only after you
                      have identified the product and want to match a tier.
            use_semantic: True for fuzzy or paraphrased queries.
            sort_by_price: True to sort cheapest first.
            use_wildcard: True for partial Thai word matches.

        Returns:
            JSON with results array, each containing logical_item_id,
            product_name, category, price_min/max, quantity_min_all/max_all,
            tiers[], award_vendors, product_spec_text, pricing_basis.
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"กำลังค้นหา: {query}", "done": False},
                }
            )

        try:
            query_vector = self._get_embedding(query)
            filter_expr = self._build_filter(
                category=category,
                year=year,
                min_price=min_price,
                max_price=max_price,
                quantity=quantity,
            )

            search_text = query if not use_wildcard else (
                f"{query}*" if not query.endswith("*") else query
            )
            # Search with at most max_search_rounds rounds: first exact, then
            # wildcard, then (optionally) the query without a trailing star.
            max_rounds = max(1, min(self.valves.max_search_rounds, 3))
            candidates = [search_text]
            if not use_wildcard and not query.endswith("*"):
                candidates.append(f"{query}*")
            if query.endswith("*"):
                candidates.append(query[:-1])
            candidates = list(dict.fromkeys(candidates))[:max_rounds]

            results_list: list[dict] = []
            for attempt in candidates:
                results_list = self._search(
                    search_text=attempt,
                    query_vector=query_vector,
                    filter_expr=filter_expr,
                    use_semantic=use_semantic,
                )
                if len(results_list) > 0:
                    break

            # Category fallback: if the caller guessed a category and nothing
            # matched, retry WITHOUT the category filter (the guess may be wrong).
            category_dropped = False
            if len(results_list) == 0 and filter_expr and category:
                no_cat_filter = self._build_filter(
                    category=None,
                    year=year,
                    min_price=min_price,
                    max_price=max_price,
                    quantity=quantity,
                )
                for attempt in candidates:
                    results_list = self._search(
                        search_text=attempt,
                        query_vector=query_vector,
                        filter_expr=no_cat_filter,
                        use_semantic=use_semantic,
                    )
                    if len(results_list) > 0:
                        category_dropped = True
                        break

            # Quantity fallback: if quantity filter killed all results, retry
            # WITHOUT it. The product's MOQ may exceed the request. Return both
            # the full product list and a flag so the LLM can report the MOQ.
            quantity_dropped = False
            if len(results_list) == 0 and filter_expr and quantity is not None:
                no_qty_filter = self._build_filter(
                    category=category,
                    year=year,
                    min_price=min_price,
                    max_price=max_price,
                    quantity=None,
                )
                for attempt in candidates:
                    results_list = self._search(
                        search_text=attempt,
                        query_vector=query_vector,
                        filter_expr=no_qty_filter,
                        use_semantic=use_semantic,
                    )
                    if len(results_list) > 0:
                        quantity_dropped = True
                        break

            if sort_by_price and results_list:
                results_list.sort(key=lambda r: r.get("price_min") if r.get("price_min") is not None else float("inf"))

            items = [self._format_result(r) for r in results_list]

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"พบ {len(items)} รายการ", "done": True},
                    }
                )

            if items:
                response = {
                    "success": True,
                    "query": query,
                    "total_results": len(items),
                    "results": items,
                }
                if category_dropped:
                    response["warning"] = (
                        f"ไม่พบผลเมื่อ filter category='{category}' → "
                        "ค้นใหม่โดยไม่ระบุ category (อาจเดาหมวดผิด) และได้ผลลัพธ์นี้"
                    )
                if quantity_dropped:
                    response["warning"] = (
                        f"ไม่พบผลเมื่อ filter quantity={quantity} → "
                        "ค้นใหม่โดยไม่ระบุจำนวน (MOQ อาจสูงกว่าที่ขอ) "
                        "ตรวจสอบ quantity_min_all ในผลลัพธ์และแจ้งผู้ใช้"
                    )
                return json.dumps(response, ensure_ascii=False, indent=2)
            return json.dumps(
                {
                    "success": True,
                    "query": query,
                    "total_results": 0,
                    "message": "ไม่พบสินค้าที่ตรงกับเงื่อนไข",
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": error_msg, "done": True},
                    }
                )
            return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)

    async def get_cheapest_option(
        self,
        query: str,
        category: Optional[str] = None,
        year: Optional[int] = None,
        __user__: dict = None,
        __request__: Request = None,
        __event_emitter__=None,
    ) -> str:
        """
        Find the cheapest awarded option for a product.

        Args:
            query: Product search query
            category: Filter by category
            year: Filter by year

        Returns:
            JSON string with cheapest option details (from price_min, no computation)
        """
        return await self.search_procurement_prices(
            query=query,
            category=category,
            year=year,
            sort_by_price=True,
            __user__=__user__,
            __request__=__request__,
            __event_emitter__=__event_emitter__,
        )

    async def compare_vendors(
        self,
        query: str,
        category: Optional[str] = None,
        year: Optional[int] = None,
        quantity: Optional[int] = None,
        __user__: dict = None,
        __request__: Request = None,
        __event_emitter__=None,
    ) -> str:
        """
        Compare awarded options for the same product.

        Args:
            query: Product search query
            category: Filter by category
            year: Filter by year
            quantity: Required quantity to match a specific tier

        Returns:
            JSON string with awarded options per tier (price_min/max + award_vendors)
        """
        return await self.search_procurement_prices(
            query=query,
            category=category,
            year=year,
            quantity=quantity,
            sort_by_price=True,
            __user__=__user__,
            __request__=__request__,
            __event_emitter__=__event_emitter__,
        )
