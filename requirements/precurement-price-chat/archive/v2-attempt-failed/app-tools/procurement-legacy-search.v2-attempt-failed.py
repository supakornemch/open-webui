"""
title: Procurement Legacy Price Search
description: Fallback search tool for legacy Trade Marketing Materials Excel (Y2026). Use when Template v2 transformation is incomplete.
author: Haadthip Engineering
version: 1.0.0
license: MIT
required_open_webui_version: 0.4.0
"""

import os
from typing import Any, Callable

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        AZURE_SEARCH_ENDPOINT: str = Field(
            default="",
            description="Azure AI Search endpoint (e.g., https://srch-entchat-poc-sand.search.windows.net)",
        )
        AZURE_SEARCH_KEY: str = Field(default="", description="Azure AI Search admin or query key")
        AZURE_SEARCH_INDEX: str = Field(
            default="procurement-legacy-prices-idx",
            description="Azure AI Search index name for legacy procurement prices",
        )
        OPENAI_API_BASE_URL: str = Field(default="", description="Azure OpenAI endpoint")
        OPENAI_API_KEY: str = Field(default="", description="Azure OpenAI API key")
        OPENAI_EMBEDDING_DEPLOYMENT: str = Field(
            default="deploy-embedding-3-large",
            description="Azure OpenAI embedding deployment name",
        )
        TOP_K: int = Field(default=10, description="Number of search results to return", ge=1, le=50)

    def __init__(self):
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        self.search_client: SearchClient | None = None
        self.openai_client: AzureOpenAI | None = None

    def _ensure_clients(self) -> None:
        if not self.search_client:
            endpoint = self.valves.AZURE_SEARCH_ENDPOINT.rstrip("/")
            key = self.valves.AZURE_SEARCH_KEY
            index = self.valves.AZURE_SEARCH_INDEX
            if not all([endpoint, key, index]):
                raise ValueError("Azure Search endpoint, key, and index are required")
            self.search_client = SearchClient(
                endpoint=endpoint,
                index_name=index,
                credential=AzureKeyCredential(key),
                api_version="2024-07-01",
            )

        if not self.openai_client:
            base_url = self.valves.OPENAI_API_BASE_URL.rstrip("/")
            api_key = self.valves.OPENAI_API_KEY
            if not all([base_url, api_key]):
                raise ValueError("OpenAI endpoint and API key are required")
            self.openai_client = AzureOpenAI(
                azure_endpoint=base_url,
                api_key=api_key,
                api_version="2024-10-21",
            )

    def _generate_embedding(self, text: str) -> list[float]:
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.valves.OPENAI_EMBEDDING_DEPLOYMENT,
            dimensions=3072,
        )
        return response.data[0].embedding

    def _build_filter(
        self,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        year: int | None = None,
    ) -> str | None:
        filters = []
        if category:
            normalized = category.strip().replace("'", "''")
            filters.append(f"category eq '{normalized}'")
        if min_price is not None:
            filters.append(f"price ge {min_price}")
        if max_price is not None:
            filters.append(f"price le {max_price}")
        if year is not None:
            filters.append(f"year eq {year}")
        return " and ".join(filters) if filters else None

    def search_legacy_procurement_prices(
        self,
        query: str,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        year: int | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """
        Search legacy procurement prices from Trade Marketing Materials Excel (Y2026).

        :param query: Search query in Thai or English (e.g., "ถังใส่น้ำแข็ง", "เสื้อยืด", "โคมไฟ")
        :param category: Filter by category (POSM(MKT), Printing(MKT), Garment, Premium, Printing-Rate)
        :param min_price: Minimum price in baht
        :param max_price: Maximum price in baht
        :param year: Filter by year (default: 2026)
        :return: JSON string with search results
        """
        try:
            self._ensure_clients()

            if __event_emitter__:
                __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Searching legacy prices for: {query}",
                            "done": False,
                        },
                    }
                )

            embedding = self._generate_embedding(query)
            vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=50, fields="content_vector")

            filter_expr = self._build_filter(
                category=category,
                min_price=min_price,
                max_price=max_price,
                year=year or 2026,
            )

            results = self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=filter_expr,
                select=[
                    "product_code",
                    "product_name",
                    "category",
                    "pricing_model",
                    "variant_description",
                    "vendor_name",
                    "price",
                    "qty",
                    "year",
                    "notes",
                    "product_description",
                    "source_workbook",
                    "source_sheet",
                    "source_row",
                    "source_item",
                    "source_qty_y2025",
                    "source_price_y2025",
                    "source_supplier_2025",
                    "source_qty_y2026",
                    "source_awarded_price",
                    "source_awarded_vendor",
                    "source_award_notes",
                    "source_history_2023_qty",
                    "source_history_2023_price",
                    "source_history_2024_qty",
                    "source_history_2024_price",
                    "source_history_2025_qty",
                    "source_history_2025_price",
                    "source_row_json",
                    "source_vendor_1",
                    "source_vendor_2",
                    "source_vendor_3",
                    "source_vendor_4",
                    "source_vendor_5",
                    "source_vendor_6",
                    "source_vendor_7",
                    "source_vendor_8",
                    "source_vendor_9",
                    "source_vendor_10",
                    "source_vendor_11",
                    "source_vendor_12",
                    "source_vendor_13",
                    "source_vendor_14",
                    "source_vendor_15",
                ],
                top=self.valves.TOP_K,
            )

            documents = list(results)

            if __event_emitter__:
                __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Found {len(documents)} legacy result(s)",
                            "done": True,
                        },
                    }
                )

            if not documents:
                return "No legacy procurement prices found matching the query."

            formatted = []
            for idx, doc in enumerate(documents, 1):
                entry = {
                    "rank": idx,
                    "product_code": doc.get("product_code", ""),
                    "product_name": doc.get("product_name", ""),
                    "category": doc.get("category", ""),
                    "pricing_model": doc.get("pricing_model", ""),
                    "variant": doc.get("variant_description", ""),
                    "vendor": doc.get("vendor_name", ""),
                    "price": doc.get("price", 0),
                    "quantity": doc.get("qty", "1"),
                    "year": doc.get("year", 2026),
                    "notes": doc.get("notes", ""),
                    "description": doc.get("product_description", ""),
                    "source": {
                        "workbook": doc.get("source_workbook", ""),
                        "sheet": doc.get("source_sheet", ""),
                        "row": doc.get("source_row", ""),
                        "item": doc.get("source_item", ""),
                        "qty_y2025": doc.get("source_qty_y2025", ""),
                        "price_y2025": doc.get("source_price_y2025", ""),
                        "supplier_2025": doc.get("source_supplier_2025", ""),
                        "qty_y2026": doc.get("source_qty_y2026", ""),
                        "awarded_price": doc.get("source_awarded_price", 0),
                        "awarded_vendor": doc.get("source_awarded_vendor", ""),
                        "award_notes": doc.get("source_award_notes", ""),
                        "history": {
                            "2023": {
                                "qty": doc.get("source_history_2023_qty", ""),
                                "price": doc.get("source_history_2023_price", ""),
                            },
                            "2024": {
                                "qty": doc.get("source_history_2024_qty", ""),
                                "price": doc.get("source_history_2024_price", ""),
                            },
                            "2025": {
                                "qty": doc.get("source_history_2025_qty", ""),
                                "price": doc.get("source_history_2025_price", ""),
                            },
                        },
                        "vendor_prices": {
                            str(vendor_number): doc.get(f"source_vendor_{vendor_number}", "")
                            for vendor_number in range(1, 16)
                            if doc.get(f"source_vendor_{vendor_number}", "")
                        },
                        "row_json": doc.get("source_row_json", ""),
                    },
                }
                formatted.append(entry)

            import json

            return json.dumps({"results": formatted, "count": len(formatted)}, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Legacy search error: {str(e)}"
            if __event_emitter__:
                __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": error_msg,
                            "done": True,
                        },
                    }
                )
            return error_msg
