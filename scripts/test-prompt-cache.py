#!/usr/bin/env python3
"""Test Azure OpenAI prompt caching through LiteLLM proxy."""
import time
import json
import sys
from openai import OpenAI

LITELLM_URL = "https://app-litellm-poc-sand.azurewebsites.net/v1"
LITELLM_KEY = "sk-litellm-poc-master-key"

# Large system prompt (~2000 tokens) to trigger caching
# Must be >= 1024 tokens for Azure prompt caching to activate
SYSTEM_PROMPT = (
    "You are an AI assistant specialized in analyzing enterprise documents and providing business intelligence. "
    + "Your role is to provide accurate, concise, and professional responses. " * 80
    + "You must always answer in English and format your responses with proper Markdown. " * 50
    + "You must reference relevant sections from the provided documents when answering questions. " * 20
    + "You are deployed behind a LiteLLM proxy that routes requests to Azure AI Foundry. " * 20
    + "Your knowledge encompasses corporate policies, HR procedures, IT guidelines, and procurement workflows. " * 15
)

client = OpenAI(base_url=LITELLM_URL, api_key=LITELLM_KEY)


def test_prompt_cache(model: str, cache_key: str = "test-cache-key-v1", rounds: int = 3) -> dict:
    """Test prompt caching by sending the same large prompt N times."""
    print(f"\n{'='*60}")
    print(f"Testing: {model} (cache_key={cache_key}, rounds={rounds})")
    print(f"{'='*60}")

    results = []
    for i in range(rounds):
        print(f"\n--- Round {i+1} ---")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Say 'hello' in one sentence. (round {i+1})"},
            ],
            temperature=0,
            max_tokens=50,
            extra_body={
                "prompt_cache_key": cache_key,
                "prompt_cache_retention": "24h",
            },
        )

        usage = resp.usage
        r = {
            "round": i + 1,
            "model": resp.model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cached_tokens": usage.prompt_tokens_details.cached_tokens if usage.prompt_tokens_details else 0,
            "content": resp.choices[0].message.content.strip(),
        }
        results.append(r)

        status = "🟢 CACHE HIT" if r["cached_tokens"] > 0 else "🔴 CACHE MISS"
        print(f"  prompt_tokens={r['prompt_tokens']}, "
              f"cached_tokens={r['cached_tokens']}, "
              f"completion={r['completion_tokens']} "
              f"→ {status}")

        # Small delay between rounds
        if i < rounds - 1:
            time.sleep(1)

    return results


def main():
    models_to_test = sys.argv[1:] if len(sys.argv) > 1 else ["gpt-5.4-nano", "gpt-5.4-mini"]

    print(f"System prompt length (chars): {len(SYSTEM_PROMPT)}")
    print(f"Estimated system prompt tokens: ~{len(SYSTEM_PROMPT) // 4}")
    print(f"Models to test: {models_to_test}")

    all_results = {}
    for model in models_to_test:
        try:
            results = test_prompt_cache(model, rounds=4)
            all_results[model] = results
        except Exception as e:
            print(f"\n❌ ERROR testing {model}: {e}")
            all_results[model] = [{"error": str(e)}]

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for model, results in all_results.items():
        cached_rounds = [r for r in results if r.get("cached_tokens", 0) > 0]
        if any("error" in r for r in results):
            print(f"  {model}: ❌ ERROR — {results[0].get('error', 'unknown')}")
        elif cached_rounds:
            first_cache = cached_rounds[0]["round"]
            print(f"  {model}: ✅ CACHE WORKS — first cache hit at round {first_cache}, "
                  f"avg cached_tokens={sum(r['cached_tokens'] for r in cached_rounds)//len(cached_rounds)}")
        else:
            print(f"  {model}: ❌ NO CACHE HITS — 0 cached_tokens in all {len(results)} rounds")

    # Cost analysis
    print(f"\n{'='*60}")
    print("COST ESTIMATE (same prompt ×3, if cache works)")
    print(f"{'='*60}")
    # nano: $0.20/1M input, $0.40/1M output. Cache read: ~$0.02/1M (90% off)
    # mini: $0.75/1M input, $1.50/1M output. Cache read: ~$0.08/1M (90% off)
    for model, results in all_results.items():
        if results and results[0].get("prompt_tokens"):
            pt = results[0]["prompt_tokens"]
            print(f"  {model}: prompt_tokens={pt} per request")
            if model == "gpt-5.4-nano":
                cache_price = 0.02  # per 1M
                no_cache_price = 0.20
            else:
                cache_price = 0.08
                no_cache_price = 0.75
            cost_3_no_cache = 3 * pt * no_cache_price / 1_000_000
            cost_3_with_cache = pt * no_cache_price / 1_000_000 + 2 * pt * cache_price / 1_000_000
            print(f"    3 calls without cache: ${cost_3_no_cache:.6f}")
            print(f"    3 calls with cache:    ${cost_3_with_cache:.6f}")
            print(f"    Savings: {100*(1-cost_3_with_cache/cost_3_no_cache):.0f}%")


if __name__ == "__main__":
    main()
