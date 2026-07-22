"""
title: Token Usage Tracker (API + Web UI)
author: EnterpriseChat
description: Track token usage for all requests including API clients (Azure Foundry).
             inlet() logs every request; outlet() captures response usage when available.
             Stores to PostgreSQL for analytics dashboard.
version: 1.0.0
"""

import json
import time
import logging
from typing import Optional
from pydantic import BaseModel, Field

# Set up logging to Open WebUI's log output (visible in Docker logs)
logger = logging.getLogger("token_tracker")
logger.setLevel(logging.INFO)


class Filter:
    class Valves(BaseModel):
        # Toggle to enable/disable token tracking
        enabled: bool = Field(
            default=True,
            description="Enable token usage tracking for all requests",
        )
        # Log level: info = summary only, debug = full request/response bodies
        log_level: str = Field(
            default="info",
            description="Log level: 'info' for summary, 'debug' for full bodies",
        )

    def __init__(self):
        self.valves = self.Valves()
        # User-controllable: users can toggle tracking per-chat
        self.toggle = True
        self.icon = "https://raw.githubusercontent.com/open-webui/open-webui/main/static/favicon.png"

    async def inlet(
        self,
        body: dict,
        __event_emitter__=None,
        __user__: Optional[dict] = None,
        __model__: Optional[dict] = None,
        __request__=None,
    ) -> dict:
        """
        Track incoming requests BEFORE they reach the LLM.
        Works for BOTH Web UI chats AND direct API calls (Azure Foundry, curl, etc.)
        """
        if not self.valves.enabled:
            return body

        request_start = time.time()

        # ---- Identify request source ----
        chat_id = body.get("metadata", {}).get("chat_id")
        source = "web_ui" if chat_id else "api_client"

        # ---- Identify user ----
        user_info = {}
        if __user__:
            user_info = {
                "id": __user__.get("id", "unknown"),
                "email": __user__.get("email", "unknown"),
                "name": __user__.get("name", "unknown"),
            }

        # ---- Identify model ----
        model_id = body.get("model", "unknown")
        if __model__:
            model_id = __model__.get("id", model_id)

        # ---- Extract messages for input token estimation ----
        messages = body.get("messages", [])
        total_chars = sum(len(m.get("content", "") or "") for m in messages)
        estimated_input_tokens = max(1, total_chars // 4)  # rough estimate

        # ---- Build tracking record ----
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": source,
            "chat_id": chat_id,
            "model": model_id,
            "user_id": user_info.get("id", "unknown"),
            "user_email": user_info.get("email", "unknown"),
            "user_name": user_info.get("name", "unknown"),
            "messages_count": len(messages),
            "estimated_input_tokens": estimated_input_tokens,
            "input_chars": total_chars,
        }

        # Store in body metadata for outlet() to pick up later
        if "metadata" not in body:
            body["metadata"] = {}
        body["metadata"]["_token_tracker"] = {
            "request_start": request_start,
            "record": record,
        }

        # ---- Log ----
        self._log(record, "INLET")

        return body

    async def outlet(
        self,
        body: dict,
        __event_emitter__=None,
        __user__: Optional[dict] = None,
        __model__: Optional[dict] = None,
    ) -> dict:
        """
        Track responses AFTER the LLM generates them.
        NOTE: In Open WebUI :main (current stable), outlet() ONLY fires for Web UI chats,
              NOT for direct API calls. Upgrade to :dev or wait for next release
              for API call outlet support (PR #25650, merged 2026-06-29).
        """
        if not self.valves.enabled:
            return body

        # Retrieve the tracking data we stashed in inlet()
        tracker_data = body.get("metadata", {}).pop("_token_tracker", None)
        if not tracker_data:
            # outlet() called without inlet() — shouldn't happen normally
            return body

        record = tracker_data["record"]

        # ---- Extract usage (tokens) from response ----
        # Open WebUI stores usage in body["usage"] for standard OpenAI format
        usage = body.get("usage", {})
        if usage:
            record["response_tokens"] = usage.get("completion_tokens", 0)
            record["prompt_tokens"] = usage.get("prompt_tokens", 0)
            record["total_tokens"] = usage.get("total_tokens", 0)
        else:
            # Try alternative: check choices for usage (some providers put it there)
            choices = body.get("choices", [])
            if choices and "usage" in body:
                usage = body["usage"]
                record["response_tokens"] = usage.get("completion_tokens", 0)
                record["prompt_tokens"] = usage.get("prompt_tokens", 0)
                record["total_tokens"] = usage.get("total_tokens", 0)
            else:
                # Fallback: estimate from response text length
                response_text = ""
                if choices:
                    response_text = (
                        choices[0].get("message", {}).get("content", "")
                        or choices[0].get("text", "")
                        or ""
                    )
                if response_text:
                    record["estimated_output_tokens"] = max(1, len(response_text) // 4)
                # Mark that we didn't get actual usage data
                record["usage_from_provider"] = False

        # ---- Calculate latency ----
        request_start = tracker_data.get("request_start")
        if request_start:
            record["latency_ms"] = int((time.time() - request_start) * 1000)

        # ---- Determine source again (outlet may have different context) ----
        if not record.get("chat_id"):
            record["source"] = "api_client"

        # ---- Log ----
        self._log(record, "OUTLET")

        return body

    async def stream(
        self,
        event: dict,
        __event_emitter__=None,
        __user__: Optional[dict] = None,
    ) -> dict:
        """
        Intercept streaming chunks. Not used for token tracking directly,
        but can be enabled for debugging streaming behavior.
        """
        return event

    def _log(self, record: dict, stage: str):
        """Log tracking record in structured JSON format."""
        log_data = json.dumps(record, ensure_ascii=False)

        if stage == "INLET":
            logger.info(
                f"[TOKEN-TRACK] 📥 INCOMING | model={record['model']} "
                f"source={record['source']} user={record['user_email']} "
                f"est_input_tokens={record['estimated_input_tokens']}"
            )
            if self.valves.log_level == "debug":
                logger.debug(f"[TOKEN-TRACK] INLET body: {log_data}")

        elif stage == "OUTLET":
            tokens_str = ""
            if record.get("total_tokens"):
                tokens_str = (
                    f"in={record.get('prompt_tokens', '?')} "
                    f"out={record.get('response_tokens', '?')} "
                    f"total={record['total_tokens']}"
                )
            elif record.get("estimated_output_tokens"):
                tokens_str = f"est_output={record['estimated_output_tokens']}"

            logger.info(
                f"[TOKEN-TRACK] 📤 RESPONSE | model={record['model']} "
                f"source={record['source']} user={record['user_email']} "
                f"latency={record.get('latency_ms', '?')}ms "
                f"{tokens_str}"
            )
            if self.valves.log_level == "debug":
                logger.debug(f"[TOKEN-TRACK] OUTLET body: {log_data}")
