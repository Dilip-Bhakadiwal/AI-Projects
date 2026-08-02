"""Quick test to verify both LLM endpoints work."""
import httpx
import asyncio
import json


async def run_llm_check(name: str, base_url: str, api_key: str, model: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/marketpulse",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly this JSON: {\"reply\": \"hello\"}"}],
        "max_tokens": 30,
        "temperature": 0.1,
    }
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            print(f"{name} status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                print(f"{name} reply: {content[:120]}")
                print(f"{name} tokens: {tokens}")
            else:
                print(f"{name} error: {r.text[:300]}")
    except Exception as e:
        print(f"{name} FAILED: {type(e).__name__}: {e}")


async def main():
    print("=== Testing OpenRouter (Gemma free) ===")
    await run_llm_check(
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        os.environ.get("OPENROUTER_API_KEY", "your-openrouter-key-here"),
        "google/gemma-4-26b-a4b-it:free",
    )

    print("\n=== Testing NVIDIA NIM (Llama 3.1 8B) ===")
    await run_llm_check(
        "NVIDIA NIM",
        "https://integrate.api.nvidia.com/v1",
        os.environ.get("NVIDIA_API_KEY", "your-nvidia-key-here"),
        "meta/llama-3.1-8b-instruct",
    )


if __name__ == "__main__":
    asyncio.run(main())
