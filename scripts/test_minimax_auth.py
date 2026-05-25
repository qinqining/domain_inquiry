import httpx

from src.config import get_minimax_settings

settings = get_minimax_settings()
payload = {
    "model": settings["model"],
    "messages": [{"role": "user", "content": "回复 OK"}],
    "max_tokens": 16,
}
headers = {
    "Authorization": f"Bearer {settings['api_key']}",
    "Content-Type": "application/json",
}

tests = [
    ("openai", "/v1/chat/completions", headers),
    ("anthropic", "/anthropic/v1/messages", headers),
    (
        "x-api-key",
        "/v1/chat/completions",
        {"X-Api-Key": settings["api_key"], "Content-Type": "application/json"},
    ),
]

for base in ("https://api.minimax.io", "https://api.minimaxi.com"):
    for name, path, hdrs in tests:
        url = f"{base}{path}"
        body = payload
        if "anthropic" in path:
            body = {
                "model": settings["model"],
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "回复 OK"}],
            }
        try:
            resp = httpx.post(url, headers=hdrs, json=body, timeout=30.0)
            print(f"{base} [{name}] -> HTTP {resp.status_code}")
            print(resp.text[:200])
        except Exception as exc:
            print(f"{base} [{name}] -> ERROR {exc}")
