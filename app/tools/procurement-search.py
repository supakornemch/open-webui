"""
title: Procurement Price Search
author: Haadthip DIO
version: 1.0
required_open_webui_version: 0.5.0

Search awarded procurement prices from Azure AI Search index (procurement-prices-th-idx).
Uses hybrid search (keyword + vector) with Thai analyzer for accurate results.

Capabilities:
- Keyword search with Thai word segmentation
- Semantic vector search for partial/fuzzy matches
- Filter by category, vendor, year, price range
- Sort by price (find cheapest options)
- Supports wildcard search for compound Thai words
- Returns only awarded quotes that meet the required specification

Authorization: Tool is available to all users with access to the model.
"""

import json
import os
from collections import defaultdict
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from fastapi import Request
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# Import Open WebUI's internal model caller
from open_webui.utils.chat import generate_chat_completion


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
            default="procurement-prices-th-idx",
            description="Search index name"
        )
        AZURE_OPENAI_ENDPOINT: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
            description="Azure OpenAI endpoint for embeddings"
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
            default=10,
            description="Maximum number of search results to return"
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
        """Generate embedding vector for text using Azure OpenAI"""
        client = AzureOpenAI(
            api_key=self.valves.AZURE_OPENAI_KEY,
            api_version=self.valves.AZURE_OPENAI_API_VERSION,
            azure_endpoint=self.valves.AZURE_OPENAI_ENDPOINT
        )
        
        response = client.embeddings.create(
            input=text,
            model=self.valves.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        
        return response.data[0].embedding

    async def _summarize_results(self, query: str, items: list, __user__: dict, __request__: Request, category: str = None, year: int = None, min_price: float = None, max_price: float = None) -> str:
        """Use Open WebUI internal LLM to summarize search results without revealing vendor names"""
        
        # Find cheapest option
        cheapest = min(items, key=lambda x: x["price"])
        
        # Group by product to show variants
        products = defaultdict(list)
        for item in items:
            key = item["product_name"]
            products[key].append(item)
        
        # Build summary prompt
        prompt = f"""คุณเป็น AI ผู้ช่วยจัดซื้อ กรุณาสรุปผลการค้นหาราคาสินค้าดังนี้:

คำค้นหา: "{query}"
จำนวนผลลัพธ์: {len(items)} รายการ

ข้อมูลสินค้า:
"""
        
        for product_name, variants in products.items():
            prompt += f"\n{product_name}:\n"
            for v in variants:
                prompt += f"  - ราคา ฿{v['price']:,.2f} ({v['qty_range'] or 'ไม่ระบุจำนวน'})\n"
        
        prompt += """
กฎการตอบ:
1. ห้ามบอกชื่อ vendor (ห้ามพูดว่า "Vendor A", "Vendor B", etc.)
2. บอกเฉพาะราคาที่ถูกที่สุด (ชนะการประกวดราคา)
3. ถ้ามีหลาย variant ให้อธิบายความแตกต่าง
4. ถ้ามี note หรือปัญหา ต้องแจ้งเตือนทันที
5. ตอบสั้น กระชับ เน้นตัวเลขและข้อมูลสำคัญ

ตัวอย่างคำตอบที่ดี:
"ร่มโค้ก ราคา ฿480/ชิ้น สำหรับ 500+ ชิ้น"

กรุณาสรุปผลการค้นหาตามกฎข้างต้น:"""
        
        # Call Open WebUI internal model
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": "คุณเป็น AI ผู้ช่วยจัดซื้อที่ตอบสั้น กระชับ และห้ามเปิดเผยชื่อ vendor"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        try:
            response = await generate_chat_completion(__request__, payload, __user__)
            summary_text = response["choices"][0]["message"]["content"]
            
            return json.dumps({
                "success": True,
                "query": query,
                "total_results": len(items),
                "summary": summary_text,
                "cheapest_price": cheapest["price"],
                "cheapest_product": cheapest["product_name"]
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            # Fallback to simple summary if LLM call fails
            return json.dumps({
                "success": True,
                "query": query,
                "total_results": len(items),
                "summary": f"{cheapest['product_name']} ราคา ฿{cheapest['price']:,.2f} ({cheapest['qty_range'] or 'ไม่ระบุ'})",
                "cheapest_price": cheapest["price"],
                "cheapest_product": cheapest["product_name"],
                "error": f"LLM summarization failed: {str(e)}"
            }, ensure_ascii=False, indent=2)

    def _build_filter(
        self,
        category: Optional[str] = None,
        vendor: Optional[str] = None,
        year: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Optional[str]:
        """Build OData filter string"""
        filters = []
        
        filters.extend(["is_winner eq true", "meets_spec eq true"])
        if category:
            filters.append(f"category eq '{category}'")
        if vendor:
            filters.append(f"vendor_code eq '{vendor}'")
        if year:
            filters.append(f"year eq {year}")
        if min_price is not None:
            filters.append(f"price ge {min_price}")
        if max_price is not None:
            filters.append(f"price le {max_price}")
        
        return " and ".join(filters) if filters else None

    async def search_procurement_prices(
        self,
        query: str,
        category: Optional[str] = None,
        vendor: Optional[str] = None,
        year: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by_price: bool = False,
        use_wildcard: bool = False,
        __user__: dict = None,
        __request__: Request = None,
        __event_emitter__=None
    ) -> str:
        """
        Search procurement prices with hybrid search (keyword + vector).
        
        Args:
            query: Search query in Thai or English (e.g. "ร่มโค้ก", "umbrella")
            category: Filter by category (POSM, Printing, Garment, etc.)
            vendor: Filter by vendor code (VEN-A, VEN-B, etc.)
            year: Filter by year (2024-2030)
            min_price: Minimum price filter
            max_price: Maximum price filter
            sort_by_price: Sort results by price ascending (find cheapest)
            use_wildcard: Use wildcard search for partial Thai word matches (e.g. "ร่ม*")
        
        Returns:
            JSON string with search results
        """
        
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"กำลังค้นหา: {query}",
                        "done": False
                    }
                }
            )
        
        try:
            # Initialize search client
            search_client = SearchClient(
                endpoint=self.valves.AZURE_SEARCH_ENDPOINT,
                index_name=self.valves.AZURE_SEARCH_INDEX,
                credential=AzureKeyCredential(self.valves.AZURE_SEARCH_KEY),
                api_version=self.valves.AZURE_SEARCH_API_VERSION
            )
            
            # Generate embedding for vector search
            query_vector = self._get_embedding(query)
            
            # Build filter
            filter_expr = self._build_filter(
                category=category,
                vendor=vendor,
                year=year,
                min_price=min_price,
                max_price=max_price
            )
            
            # Prepare vector query
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=50,
                fields="content_vector"
            )
            
            # Try exact match first
            search_text = query if not use_wildcard else (f"{query}*" if not query.endswith("*") else query)
            
            # Execute hybrid search (fulltext + vector)
            # API version 2026-04-01 supports native hybrid search
            results = search_client.search(
                search_text=search_text,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=self.valves.max_results,
                select=[
                    "product_code", "product_name", "category", "pricing_model",
                    "variant_code", "variant_description", "vendor_code", "vendor_name",
                    "year", "price", "qty", "qty_range"
                ],
                order_by=["price asc"] if sort_by_price else None
            )
            
            # Convert iterator to list to ensure results are captured
            results_list = list(results)
            
            # If no results with exact match and wildcard not used, retry with wildcard
            if len(results_list) == 0 and not use_wildcard and not query.endswith("*"):
                search_text = f"{query}*"
                results = search_client.search(
                    search_text=search_text,
                    vector_queries=[vector_query],
                    filter=filter_expr,
                    top=self.valves.max_results,
                    select=[
                        "product_code", "product_name", "category", "pricing_model",
                        "variant_code", "variant_description", "vendor_code", "vendor_name",
                        "year", "price", "qty", "qty_range"
                    ],
                    order_by=["price asc"] if sort_by_price else None
                )
                results_list = list(results)
            
            # Format results
            items = []
            for result in results_list:
                items.append({
                    "product_code": result.get("product_code"),
                    "product_name": result.get("product_name"),
                    "category": result.get("category"),
                    "pricing_model": result.get("pricing_model"),
                    "variant_code": result.get("variant_code"),
                    "variant_description": result.get("variant_description"),
                    "vendor_code": result.get("vendor_code"),
                    "vendor_name": result.get("vendor_name"),
                    "year": result.get("year"),
                    "price": result.get("price"),
                    "qty": result.get("qty"),
                    "qty_range": result.get("qty_range"),
                    "score": result.get("@search.score")
                })
            
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"พบ {len(items)} รายการ",
                            "done": True
                        }
                    }
                )
            
            # Return results directly (no LLM summarization for now - debugging)
            if len(items) > 0:
                return json.dumps({
                    "success": True,
                    "query": query,
                    "total_results": len(items),
                    "results": items
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": True,
                    "query": query,
                    "total_results": 0,
                    "message": "ไม่พบสินค้าที่ตรงกับเงื่อนไข"
                }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": error_msg,
                            "done": True
                        }
                    }
                )
            
            return json.dumps({
                "success": False,
                "error": error_msg
            }, ensure_ascii=False)

    async def get_cheapest_option(
        self,
        query: str,
        category: Optional[str] = None,
        year: Optional[int] = None,
        __user__: dict = None,
        __request__: Request = None,
        __event_emitter__=None
    ) -> str:
        """
        Find the cheapest procurement option for a product.
        
        Args:
            query: Product search query
            category: Filter by category
            year: Filter by year
        
        Returns:
            JSON string with cheapest option details
        """
        return await self.search_procurement_prices(
            query=query,
            category=category,
            year=year,
            sort_by_price=True,
            __user__=__user__,
            __request__=__request__,
            __event_emitter__=__event_emitter__
        )

    async def compare_vendors(
        self,
        product_code: str,
        variant_code: Optional[str] = None,
        year: Optional[int] = None,
        __user__: dict = None,
        __request__: Request = None,
        __event_emitter__=None
    ) -> str:
        """
        Compare prices across vendors for a specific product/variant.
        
        Args:
            product_code: Product code (e.g. POSM_001)
            variant_code: Variant code (e.g. POSM_001_V1)
            year: Filter by year
        
        Returns:
            JSON string with vendor comparison
        """
        query = f"{product_code} {variant_code}" if variant_code else product_code
        
        return await self.search_procurement_prices(
            query=query,
            year=year,
            sort_by_price=True,
            __user__=__user__,
            __request__=__request__,
            __event_emitter__=__event_emitter__
        )
