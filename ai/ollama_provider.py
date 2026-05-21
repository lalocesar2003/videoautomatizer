import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def call_ollama_json(
    messages: list[dict[str, str]],
    schema: dict[str, Any],
) -> dict[str, Any]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "messages": messages,
        "format": schema,
        "options": {
            "temperature": 0,
        },
    }

    raw_response = post_json(url, payload)
    content = raw_response.get("message", {}).get("content", "")

    if not content:
        raise ValueError("Ollama no devolvió contenido JSON.")

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"Ollama devolvió JSON inválido:\n{content}") from error


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama respondió con error HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(
            "No se pudo conectar con Ollama. "
            "Verifica que esté corriendo en OLLAMA_BASE_URL."
        ) from error
