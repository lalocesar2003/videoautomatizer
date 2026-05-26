from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


READY_STATUSES = {"ready", "fallback_stock", "placeholder"}
PENDING_STATUSES = {
    "needs_self_recording",
    "needs_screen_recording",
    "needs_manual_review",
    "needs_fallback_search",
    "missing_asset",
}


def generate_timeline(
    *,
    scenes_data: dict[str, Any],
    visual_plan_data: dict[str, Any],
    resolved_assets_data: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    scenes = scenes_data.get("scenes", [])
    visual_plan_by_scene = index_by_scene(visual_plan_data.get("visual_plan", []))
    resolved_assets_by_scene = index_by_scene(
        resolved_assets_data.get("resolved_assets", [])
    )

    timeline_items = []

    for scene in scenes:
        scene_number = int_or_zero(scene.get("scene"))
        visual_plan = visual_plan_by_scene.get(scene_number, {})
        resolved_asset = resolved_assets_by_scene.get(scene_number, {})

        timeline_items.append(
            build_timeline_item(
                scene=scene,
                visual_plan=visual_plan,
                resolved_asset=resolved_asset,
            )
        )

    timeline_items.sort(key=lambda item: (item["start_seconds"], item["scene"]))

    return {
        "project_title": get_project_title(
            scenes_data,
            visual_plan_data,
            resolved_assets_data,
        ),
        "generated_at": generated_at or utc_now_iso(),
        "timeline": timeline_items,
        "summary": build_summary(timeline_items),
    }


def build_timeline_item(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    resolved_asset: dict[str, Any],
) -> dict[str, Any]:
    scene_number = int_or_zero(scene.get("scene"))
    start = clean_string(scene.get("start"))
    end = clean_string(scene.get("end"))
    start_seconds = parse_timecode(start)
    end_seconds = parse_timecode(end)
    duration_seconds = end_seconds - start_seconds

    if duration_seconds <= 0:
        raise ValueError(
            f"La escena {scene_number} tiene duración inválida: {start} - {end}."
        )

    status = clean_string(resolved_asset.get("status")) or "missing_asset"
    resolution_type = clean_string(resolved_asset.get("resolution_type")) or "missing_asset"
    asset_type = (
        clean_string(resolved_asset.get("asset_type"))
        or clean_string(visual_plan.get("asset_type"))
        or "unknown"
    )

    return {
        "scene": scene_number,
        "start": start,
        "end": end,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "section": scene.get("section", ""),
        "asset_type": asset_type,
        "resolution_type": resolution_type,
        "status": status,
        "clip_path": build_clip_path(
            scene_number=scene_number,
            resolution_type=resolution_type,
            status=status,
            selected_clip=resolved_asset.get("selected_clip"),
        ),
        "primary_action": (
            resolved_asset.get("primary_action")
            or visual_plan.get("primary_action")
            or scene.get("visual", "")
        ),
        "visual_intent": (
            resolved_asset.get("visual_intent")
            or visual_plan.get("visual_intent")
            or scene.get("text_on_screen", "")
        ),
        "text_on_screen": scene.get("text_on_screen", ""),
        "audio": scene.get("audio", ""),
        "message": resolved_asset.get("message", ""),
    }


def parse_timecode(value: str) -> int:
    cleaned = clean_string(value)
    parts = cleaned.split(":")

    if len(parts) not in {2, 3}:
        raise ValueError(
            f"Formato de tiempo inválido: {value}. Usa M:SS o H:MM:SS."
        )

    if not all(part.isdigit() for part in parts):
        raise ValueError(
            f"Formato de tiempo inválido: {value}. Usa solo números y ':'."
        )

    numbers = [int(part) for part in parts]

    if len(numbers) == 2:
        minutes, seconds = numbers
        validate_clock_part(seconds, "segundos", value)
        return minutes * 60 + seconds

    hours, minutes, seconds = numbers
    validate_clock_part(minutes, "minutos", value)
    validate_clock_part(seconds, "segundos", value)
    return hours * 3600 + minutes * 60 + seconds


def validate_clock_part(part: int, label: str, original_value: str) -> None:
    if part >= 60:
        raise ValueError(
            f"Formato de tiempo inválido: {original_value}. "
            f"Los {label} deben ser menores a 60."
        )


def build_clip_path(
    *,
    scene_number: int,
    resolution_type: str,
    status: str,
    selected_clip: dict[str, Any] | None,
) -> str | None:
    if status in PENDING_STATUSES:
        return None

    if resolution_type == "placeholder":
        return None

    if resolution_type == "local" and status == "ready":
        extension = get_local_clip_extension(selected_clip or {})
        return build_export_clip_path(scene_number, extension)

    if resolution_type == "pexels" and status == "ready":
        return build_export_clip_path(scene_number, ".mp4")

    if resolution_type == "fallback_stock" and selected_clip:
        return build_export_clip_path(scene_number, ".mp4")

    return None


def get_local_clip_extension(selected_clip: dict[str, Any]) -> str:
    local_path = clean_string(selected_clip.get("local_path"))
    extension = Path(local_path).suffix.lower()

    return extension or ".mp4"


def build_export_clip_path(scene_number: int, extension: str) -> str:
    return f"exports/clips/scene_{scene_number:02d}_clip_01{extension}"


def build_summary(timeline_items: list[dict[str, Any]]) -> dict[str, int]:
    ready_count = sum(1 for item in timeline_items if item.get("status") in READY_STATUSES)
    pending_count = len(timeline_items) - ready_count
    total_duration_seconds = max(
        (item.get("end_seconds", 0) for item in timeline_items),
        default=0,
    )

    return {
        "scene_count": len(timeline_items),
        "ready_count": ready_count,
        "pending_count": pending_count,
        "total_duration_seconds": total_duration_seconds,
    }


def index_by_scene(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed = {}

    for item in items:
        scene_number = int_or_zero(item.get("scene"))

        if scene_number:
            indexed[scene_number] = item

    return indexed


def get_project_title(*sources: dict[str, Any]) -> str:
    for source in sources:
        title = clean_string(source.get("project_title"))
        if title:
            return title

    return "Proyecto sin título"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
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
