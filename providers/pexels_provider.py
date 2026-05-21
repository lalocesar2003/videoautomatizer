import json
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
DEFAULT_PER_PAGE = 5

HttpGet = Callable[[str, dict[str, str]], dict[str, Any]]


def search_pexels_for_visual_plan(
    visual_plan_data: dict[str, Any],
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    api_key = get_pexels_api_key()
    format_name = visual_plan_data.get("format") or "Vertical"
    orientation = get_pexels_orientation(format_name)

    results = []

    for item in visual_plan_data.get("visual_plan", []):
        if not item.get("needs_pexels"):
            continue

        query = clean_string(item.get("search_query_en"))

        if not query:
            raise ValueError(
                f"Escena {item.get('scene')} tiene needs_pexels=true, "
                "pero no tiene search_query_en."
            )

        response = search_videos(
            query=query,
            api_key=api_key,
            orientation=orientation,
            http_get=http_get,
        )

        results.append(
            {
                "scene": item.get("scene"),
                "asset_type": item.get("asset_type"),
                "visual_intent": clean_string(item.get("visual_intent")),
                "query": query,
                "suggestions": normalize_pexels_videos(response.get("videos", [])),
            }
        )

    return {
        "project_title": visual_plan_data.get("project_title", "Proyecto sin título"),
        "format": format_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }


def search_videos(
    *,
    query: str,
    api_key: str,
    orientation: str | None,
    per_page: int = DEFAULT_PER_PAGE,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    params = {
        "query": query,
        "per_page": str(per_page),
    }

    if orientation:
        params["orientation"] = orientation

    url = f"{PEXELS_SEARCH_URL}?{urlencode(params)}"
    headers = {
        "Authorization": api_key,
        "Accept": "application/json",
        "User-Agent": "videosstock-broll-mvp/1.0",
    }

    return (http_get or get_json)(url, headers)


def normalize_pexels_videos(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions = []

    for video in videos:
        width = int_or_zero(video.get("width"))
        height = int_or_zero(video.get("height"))

        suggestions.append(
            {
                "provider": "pexels",
                "provider_id": str(video.get("id", "")),
                "page_url": clean_string(video.get("url")),
                "thumbnail_url": get_thumbnail_url(video),
                "preview_url": get_preview_url(video),
                "duration": int_or_zero(video.get("duration")),
                "width": width,
                "height": height,
                "orientation": detect_orientation(width, height),
                "author_name": clean_string(video.get("user", {}).get("name")),
                "author_url": clean_string(video.get("user", {}).get("url")),
            }
        )

    return suggestions


def get_preview_url(video: dict[str, Any]) -> str:
    video_files = video.get("video_files", [])

    if not isinstance(video_files, list) or not video_files:
        return ""

    sorted_files = sorted(
        video_files,
        key=lambda item: int_or_zero(item.get("width")) * int_or_zero(item.get("height")),
        reverse=True,
    )

    return clean_string(sorted_files[0].get("link"))


def get_thumbnail_url(video: dict[str, Any]) -> str:
    pictures = video.get("video_pictures", [])

    if isinstance(pictures, list) and pictures:
        return clean_string(pictures[0].get("picture"))

    return clean_string(video.get("image"))


def get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    ssl_context = build_ssl_context()

    try:
        with urlopen(request, timeout=30, context=ssl_context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(build_pexels_http_error(error.code, detail)) from error
    except URLError as error:
        raise RuntimeError(
            "No se pudo conectar con Pexels. Revisa tu conexión o intenta más tarde."
        ) from error


def build_ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
    except ModuleNotFoundError:
        return None

    return ssl.create_default_context(cafile=certifi.where())


def build_pexels_http_error(status_code: int, detail: str) -> str:
    if status_code in {401, 403}:
        return (
            f"Pexels rechazó la solicitud con HTTP {status_code}. "
            "Revisa que PEXELS_API_KEY sea válida y tenga acceso a la API. "
            f"Detalle: {detail}"
        )

    if status_code == 429:
        return (
            "Pexels respondió HTTP 429. "
            "Probablemente alcanzaste el límite de requests. "
            f"Detalle: {detail}"
        )

    return f"Pexels respondió con error HTTP {status_code}: {detail}"


def get_pexels_api_key() -> str:
    api_key = os.getenv("PEXELS_API_KEY", "").strip() or read_env_value("PEXELS_API_KEY")

    if not api_key or api_key == "tu_api_key_aqui":
        raise RuntimeError(
            "Falta PEXELS_API_KEY. Configura tu archivo .env con una API key válida."
        )

    return api_key


def read_env_value(key: str, env_path: Path = Path(".env")) -> str:
    if not env_path.exists():
        return ""

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()

        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue

        name, value = clean_line.split("=", 1)

        if name.strip() == key:
            return value.strip().strip('"').strip("'")

    return ""


def get_pexels_orientation(format_name: str) -> str | None:
    if format_name.lower() in {"vertical", "portrait"}:
        return "portrait"

    return None


def detect_orientation(width: int, height: int) -> str:
    if height > width:
        return "vertical"

    if width > height:
        return "horizontal"

    return "square"


def clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
