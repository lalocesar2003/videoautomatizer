import json
import re
from pathlib import Path
from typing import Any


LOCAL_ASSET_CHOICE = "local_asset"
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def save_selected_assets(path: Path, selected_assets: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(selected_assets, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_selected_assets(
    scored_results: dict[str, Any],
    selected_provider_ids: set[str],
) -> dict[str, Any]:
    selected_assets = []

    for scene in scored_results.get("results", []):
        for suggestion in scene.get("suggestions", []):
            provider_id = clean_string(suggestion.get("provider_id"))

            if provider_id not in selected_provider_ids:
                continue

            selected_assets.append(
                {
                    "scene": scene.get("scene"),
                    "asset_type": scene.get("asset_type"),
                    "visual_intent": scene.get("visual_intent"),
                    "query": scene.get("query"),
                    "selected_clip": build_selected_clip(suggestion),
                }
            )

    return {
        "project_title": scored_results.get("project_title", "Proyecto sin título"),
        "selected_assets": selected_assets,
    }


def build_selected_assets_from_scene_choices(
    *,
    project_title: str,
    scenes: list[dict[str, Any]],
    visual_plan_by_scene: dict[int, dict[str, Any]],
    scored_results_by_scene: dict[int, dict[str, Any]],
    choices_by_scene: dict[int, str],
    local_assets_by_scene: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selected_assets = []
    local_assets_by_scene = local_assets_by_scene or {}

    for scene in scenes:
        scene_number = int_or_zero(scene.get("scene"))
        choice = clean_string(choices_by_scene.get(scene_number))

        if not choice:
            continue

        visual_plan = visual_plan_by_scene.get(scene_number, {})
        scored_scene = scored_results_by_scene.get(scene_number, {})

        if choice == "manual_task":
            selected_assets.append(
                build_manual_task_selection(scene, visual_plan)
            )
            continue

        if choice == LOCAL_ASSET_CHOICE:
            selected_assets.append(
                build_local_asset_selection(
                    scene=scene,
                    visual_plan=visual_plan,
                    local_asset=local_assets_by_scene.get(scene_number, {}),
                )
            )
            continue

        suggestion = find_suggestion_by_provider_id(scored_scene, choice)

        if suggestion:
            selected_assets.append(
                {
                    "scene": scene_number,
                    "asset_type": visual_plan.get("asset_type") or scored_scene.get("asset_type"),
                    "selection_type": "pexels",
                    "visual_intent": visual_plan.get("visual_intent") or scored_scene.get("visual_intent"),
                    "query": scored_scene.get("query") or visual_plan.get("search_query_en", ""),
                    "selected_clip": build_selected_clip(suggestion),
                }
            )

    return {
        "project_title": project_title or "Proyecto sin título",
        "selected_assets": selected_assets,
    }


def build_local_asset_selection(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    local_asset: dict[str, Any],
) -> dict[str, Any]:
    scene_number = int_or_zero(scene.get("scene"))
    local_path = clean_string(local_asset.get("local_path"))

    if not local_path:
        raise ValueError(
            f"La escena {scene_number} está marcada como asset local, "
            "pero no tiene archivo local asignado."
        )

    validate_video_extension(Path(local_path).suffix)
    asset_type = clean_string(visual_plan.get("asset_type")) or "local"

    return {
        "scene": scene_number,
        "asset_type": asset_type,
        "selection_type": "local",
        "visual_intent": visual_plan.get("visual_intent", ""),
        "query": visual_plan.get("search_query_en", ""),
        "selected_clip": {
            "provider": "local",
            "local_path": local_path,
            "original_filename": clean_string(local_asset.get("original_filename")),
        },
    }


def build_manual_task_selection(
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
) -> dict[str, Any]:
    asset_type = clean_string(visual_plan.get("asset_type")) or "manual"
    task_type = get_manual_task_type(asset_type)

    return {
        "scene": scene.get("scene"),
        "asset_type": asset_type,
        "selection_type": "manual_task",
        "visual_intent": visual_plan.get("visual_intent", ""),
        "query": visual_plan.get("search_query_en", ""),
        "manual_task": {
            "task_type": task_type,
            "primary_action": visual_plan.get("primary_action") or scene.get("visual", ""),
            "status": "pending",
        },
    }


def get_manual_task_type(asset_type: str) -> str:
    if asset_type == "self_recorded":
        return "self_recording"

    if asset_type == "screen_recording":
        return "screen_recording"

    return "manual_review"


def find_suggestion_by_provider_id(
    scored_scene: dict[str, Any],
    provider_id: str,
) -> dict[str, Any] | None:
    for suggestion in scored_scene.get("suggestions", []):
        if clean_string(suggestion.get("provider_id")) == provider_id:
            return suggestion

    return None


def build_selected_clip(suggestion: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": suggestion.get("provider"),
        "provider_id": suggestion.get("provider_id"),
        "page_url": suggestion.get("page_url"),
        "preview_url": suggestion.get("preview_url"),
        "thumbnail_url": suggestion.get("thumbnail_url"),
        "duration": suggestion.get("duration"),
        "width": suggestion.get("width"),
        "height": suggestion.get("height"),
        "orientation": suggestion.get("orientation"),
        "author_name": suggestion.get("author_name"),
        "score": suggestion.get("score"),
        "score_breakdown": suggestion.get("score_breakdown", {}),
    }


def get_selected_provider_ids(selected_assets: dict[str, Any]) -> set[str]:
    provider_ids = set()

    for item in selected_assets.get("selected_assets", []):
        selected_clip = item.get("selected_clip", {})
        provider_id = clean_string(selected_clip.get("provider_id"))

        if provider_id:
            provider_ids.add(provider_id)

    return provider_ids


def get_local_assets_by_scene(selected_assets: dict[str, Any]) -> dict[int, dict[str, Any]]:
    local_assets = {}

    for item in selected_assets.get("selected_assets", []):
        scene_number = int_or_zero(item.get("scene"))
        selection_type = clean_string(item.get("selection_type"))
        selected_clip = item.get("selected_clip", {})
        provider = clean_string(selected_clip.get("provider"))

        if selection_type == "local" or provider == "local":
            local_assets[scene_number] = selected_clip

    return local_assets


def get_choices_by_scene(selected_assets: dict[str, Any]) -> dict[int, str]:
    choices = {}

    for item in selected_assets.get("selected_assets", []):
        scene_number = int_or_zero(item.get("scene"))
        selection_type = clean_string(item.get("selection_type"))
        selected_clip = item.get("selected_clip", {})
        provider = clean_string(selected_clip.get("provider"))

        if selection_type == "local" or provider == "local":
            choices[scene_number] = LOCAL_ASSET_CHOICE
            continue

        if selection_type == "manual_task":
            choices[scene_number] = "manual_task"
            continue

        provider_id = clean_string(selected_clip.get("provider_id"))

        if provider_id:
            choices[scene_number] = provider_id

    return choices


def save_uploaded_local_asset(
    *,
    local_assets_dir: Path,
    scene_number: int,
    original_filename: str,
    content: bytes,
) -> dict[str, str]:
    filename = build_local_asset_filename(scene_number, original_filename)
    output_path = local_assets_dir / filename

    local_assets_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)

    return {
        "local_path": str(output_path),
        "original_filename": Path(original_filename).name,
    }


def build_local_asset_filename(scene_number: int, original_filename: str) -> str:
    original_path = Path(clean_string(original_filename)).name
    suffix = Path(original_path).suffix.lower()
    validate_video_extension(suffix)

    stem = sanitize_filename_stem(Path(original_path).stem)
    return f"scene_{scene_number:02d}_{stem}{suffix}"


def sanitize_filename_stem(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", clean_string(value)).strip("_")
    return cleaned or "asset"


def validate_video_extension(extension: str) -> None:
    normalized_extension = clean_string(extension).lower()

    if normalized_extension not in SUPPORTED_VIDEO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
        raise ValueError(
            f"Extensión de video no soportada: {normalized_extension or '(vacía)'}. "
            f"Usa una de estas: {supported}."
        )


def count_suggestions(scored_results: dict[str, Any]) -> int:
    return sum(
        len(scene.get("suggestions", []))
        for scene in scored_results.get("results", [])
    )


def clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
