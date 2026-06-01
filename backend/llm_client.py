import json
import urllib.request
import urllib.error
from typing import Optional


def check_ollama() -> bool:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=2)
        return True
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        return False


def list_ollama_models() -> list[str]:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def pull_ollama_model(model: str = "llama3.2:3b") -> bool:
    try:
        data = json.dumps({"name": model}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/pull", data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def ask_ollama(prompt: str, model: str = "llama3.2:3b", system: str = "",
               max_tokens: int = 600, temperature: float = 0.3) -> Optional[str]:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate", data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result.get("response", "").strip()
    except Exception:
        return None


def ask_openai(prompt: str, api_key: str, model: str = "gpt-4o-mini",
               system: str = "", max_tokens: int = 600) -> Optional[str]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None
