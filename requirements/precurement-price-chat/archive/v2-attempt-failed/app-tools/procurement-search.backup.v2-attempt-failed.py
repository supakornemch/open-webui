"""
title: Procurement Price Search
author: Haadthip DIO
version: 2.0
required_open_webui_version: 0.5.0

Search awarded procurement prices from Azure AI Search index (procurement-prices-th-idx).

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
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from fastapi import Request
from openai import AzureOpenAI
from pydantic import BaseModel, Field


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
        if not self.valves.AZURE_SEARCH_KEY:
            self.valves.AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
        if not self.valves.AZURE_OPENAI_KEY:
            self.valves.AZURE_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
        if self.valves.AZURE_OPENAI_ENDPOINT == "https://aif-entchat-poc-sand.cognitiveservices.azure.com":
            self.valves.AZURE_OPENAI_ENDPOINT = os.getenv(
                "OPENAI_API_BASE_URL", self.valves.AZURE_OPENAI_ENDPOINT
            )
        self.valves.SHAREPOINT_SITE_HOST = self.valves.SHAREPOINT_SITE_HOST or os.getenv(
            "SHAREPOINT_SITE_HOST", ""
        )
        self.valves.SHAREPOINT_SITE_PATH = self.valves.SHAREPOINT_SITE_PATH or os.getenv(
            "SHAREPOINT_SITE_PATH", ""
        )
        self.valves.SHAREPOINT_FILE_PATH = self.valves.SHAREPOINT_FILE_PATH or os.getenv(
            "SHAREPOINT_FILE_PATH", ""
        )
        self._sharepoint_cache = None

    @staticmethod
    def _is_true(value) -> bool:
        return str(value).strip().upper() in {"TRUE", "YES", "1"}

    @staticmethod
    def _related_products(product: dict, quote: dict) -> list[str]:
        """Return explicitly declared items that need a separate price lookup."""
        values = [str(product.get("Related Products Code", "") or "").strip()]
        notes = str(quote.get("Notes", "") or product.get("Notes", "") or "")
        match = re.search(r"\bRELATED_PRODUCTS?\s*:\s*([^\r\n]+)", notes, re.IGNORECASE)
        if match:
            values.append(match.group(1))

        related = []
        for value in values:
            for item in re.split(r"[;|\r\n]+", value):
                item = item.strip()
                if item and item not in related:
                    related.append(item)
        return related

    def _graph_token(self) -> str:
        delegated_token = (
            self.user_valves.SHAREPOINT_ACCESS_TOKEN.strip()
            or os.getenv("SHAREPOINT_ACCESS_TOKEN", "").strip()
        )
        if delegated_token:
            return delegated_token.removeprefix("Bearer ").strip()

        tenant_id = os.getenv("MICROSOFT_CLIENT_TENANT_ID") or os.getenv("MICROSOFT_TENANT", "")
        client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
        client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "")
        if not all((tenant_id, client_id, client_secret)):
            raise RuntimeError(
                "ตั้งค่า SHAREPOINT_ACCESS_TOKEN หรือ MICROSOFT_CLIENT_TENANT_ID, "
                "MICROSOFT_CLIENT_ID และ MICROSOFT_CLIENT_SECRET"
            )
        response = requests.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _download_sharepoint_workbook(self) -> Optional[tuple[str, bytes, str]]:
        if not all((self.valves.SHAREPOINT_SITE_HOST, self.valves.SHAREPOINT_SITE_PATH, self.valves.SHAREPOINT_FILE_PATH)):
            return None
        token = self._graph_token()
        headers = {"Authorization": f"Bearer {token}"}
        site_path = self.valves.SHAREPOINT_SITE_PATH.strip("/")
        site_response = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{self.valves.SHAREPOINT_SITE_HOST}:/{site_path}",
            headers=headers,
            timeout=30,
        )
        site_response.raise_for_status()
        site_id = site_response.json()["id"]
        item_path = self.valves.SHAREPOINT_FILE_PATH.strip("/")
        metadata_response = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{item_path}",
            headers=headers,
            timeout=30,
        )
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        etag = metadata.get("eTag", "")
        if self._sharepoint_cache and self._sharepoint_cache[0] == etag:
            return self._sharepoint_cache[1], self._sharepoint_cache[2], etag
        content_response = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{metadata['id']}/content",
            headers=headers,
            timeout=90,
            allow_redirects=True,
        )
        content_response.raise_for_status()
        self._sharepoint_cache = (etag, metadata.get("name", item_path), content_response.content)
        return metadata.get("name", item_path), content_response.content, etag

    def _load_sharepoint_records(self) -> tuple[str, list[dict]]:
        filename, workbook, _ = self._download_sharepoint_workbook()
        sheets = pd.read_excel(io.BytesIO(workbook), sheet_name=["Products", "Variants", "Vendors", "Vendor_Prices"])
        required = {"Products", "Variants", "Vendors", "Vendor_Prices"}
        if required - set(sheets):
            raise ValueError(f"ไฟล์ {filename} ต้องมีชีต: {', '.join(sorted(required))}")
        products = sheets["Products"].fillna("").set_index("Product Code").to_dict("index")
        variants = sheets["Variants"].fillna("").set_index("Variant Code").to_dict("index")
        vendors = sheets["Vendors"].fillna("").set_index("Vendor Code").to_dict("index")
        records = []
        for _, quote in sheets["Vendor_Prices"].fillna("").iterrows():
            if not self._is_true(quote.get("Is Winner")) or not self._is_true(quote.get("Meets Spec")):
                continue
            product_code = str(quote.get("Product Code", "")).strip()
            variant_code = str(quote.get("Variant Code", "")).strip()
            vendor_code = str(quote.get("Vendor Code", "")).strip()
            product = products.get(product_code)
            vendor = vendors.get(vendor_code)
            variant = variants.get(variant_code, {}) if variant_code else {}
            if not product or not vendor or (variant_code and not variant):
                continue
            records.append({
                "product_code": product_code,
                "product_name": str(product.get("Product Name", "")).strip(),
                "category": str(product.get("Category", "")).strip(),
                "pricing_model": str(product.get("Pricing Model", "")).strip(),
                "variant_code": variant_code,
                "variant_description": str(variant.get("Description", "")).strip(),
                "vendor_code": vendor_code,
                "vendor_name": str(vendor.get("Vendor Name", "")).strip(),
                "year": int(quote["Year"]),
                "price": float(quote["Price"]),
                "qty": quote.get("Qty", ""),
                "qty_range": str(quote.get("Qty Range", "")).strip(),
                "notes": str(quote.get("Notes", "") or "").strip(),
                "related_products": self._related_products(product, quote),
            })
        if not records:
            raise ValueError(f"ไม่พบ quote ที่ Is Winner และ Meets Spec เป็น TRUE ใน {filename}")
        return filename, records

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token for token in re.split(r"[\s,/.()\-]+", text.lower()) if len(token) > 1]

    async def _search_sharepoint_records(
        self,
        query: str,
        category: Optional[str],
        vendor: Optional[str],
        year: Optional[int],
        min_price: Optional[float],
        max_price: Optional[float],
        sort_by_price: bool,
    ) -> Optional[dict]:
        if not all((self.valves.SHAREPOINT_SITE_HOST, self.valves.SHAREPOINT_SITE_PATH, self.valves.SHAREPOINT_FILE_PATH)):
            return None
        filename, records = self._load_sharepoint_records()

        query_tokens = self._tokens(query)
        ranked = []
        for record in records:
            if category and record.get("category", "").lower() != category.lower():
                continue
            if vendor and record.get("vendor_code", "").lower() != vendor.lower():
                continue
            if year and record.get("year") != year:
                continue
            if min_price is not None and record.get("price", 0) < min_price:
                continue
            if max_price is not None and record.get("price", 0) > max_price:
                continue

            searchable = " ".join(
                str(record.get(field, ""))
                for field in ("product_name", "variant_description", "category", "product_code")
            ).lower()
            matched = sum(token in searchable for token in query_tokens)
            if query.lower() in searchable:
                matched += max(2, len(query_tokens))
            if matched:
                ranked.append((matched, record))

        ranked.sort(key=lambda item: (item[0], -item[1].get("price", 0)), reverse=True)
        results = [
            {
                "product_code": record.get("product_code"),
                "product_name": record.get("product_name"),
                "category": record.get("category"),
                "pricing_model": record.get("pricing_model"),
                "variant_code": record.get("variant_code"),
                "variant_description": record.get("variant_description"),
                "vendor_code": record.get("vendor_code"),
                "vendor_name": record.get("vendor_name"),
                "year": record.get("year"),
                "price": record.get("price"),
                "qty": record.get("qty"),
                "qty_range": record.get("qty_range"),
                "notes": record.get("notes"),
                "related_products": record.get("related_products", []),
                "source": f"SharePoint: {filename}",
            }
            for _, record in ranked[:self.valves.max_results]
        ]
        if sort_by_price:
            results.sort(key=lambda record: record["price"])
        return {
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results,
            "source": f"SharePoint: {filename}",
        }

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
            sharepoint_result = await self._search_sharepoint_records(
                query=query,
                category=category,
                vendor=vendor,
                year=year,
                min_price=min_price,
                max_price=max_price,
                sort_by_price=sort_by_price,
            )
            if sharepoint_result is not None:
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"พบ {sharepoint_result['total_results']} รายการจาก SharePoint",
                                "done": True,
                            },
                        }
                    )
                return json.dumps(sharepoint_result, ensure_ascii=False, indent=2)

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
                    "year", "price", "qty", "qty_range", "notes", "related_products"
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
                        "year", "price", "qty", "qty_range", "notes", "related_products"
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
                    "notes": result.get("notes"),
                    "related_products": result.get("related_products", []),
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
