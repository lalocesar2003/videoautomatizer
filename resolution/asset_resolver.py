from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


READY_STATUSES = {"ready", "fallback_stock", "placeholder"}
ALLOWED_RESOLUTION_TYPES = {
    "pexels",
    "local",
    "fallback_stock",
    "placeholder",
    "missing_asset",
}


def resolve_assets(
    *,
    scenes_data: dict[str, Any],
    visual_plan_data: dict[str, Any],
    selected_assets_data: dict[str, Any],
    resolution_choices_data: dict[str, Any] | None = None,
    scored_results_data: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Resolve every scene into a timeline-ready asset decision."""
    scenes = scenes_data.get("scenes", [])
    visual_plan_by_scene = index_by_scene(visual_plan_data.get("visual_plan", []))
    selected_assets_by_scene = index_by_scene(
        selected_assets_data.get("selected_assets", [])
    )
    choices_by_scene = index_by_scene(
        (resolution_choices_data or {}).get("resolutions", [])
    )
    scored_results_by_scene = index_by_scene(
        (scored_results_data or {}).get("results", [])
    )

    resolved_assets = []

    for scene in scenes:
        scene_number = int_or_zero(scene.get("scene"))
        visual_plan = visual_plan_by_scene.get(scene_number, {})
        selected_asset = selected_assets_by_scene.get(scene_number)
        resolution_choice = choices_by_scene.get(scene_number)
        scored_scene = scored_results_by_scene.get(scene_number, {})

        resolved_assets.append(
            resolve_scene(
                scene=scene,
                visual_plan=visual_plan,
                selected_asset=selected_asset,
                resolution_choice=resolution_choice,
                scored_scene=scored_scene,
            )
        )

    return {
        "project_title": get_project_title(
            scenes_data,
            visual_plan_data,
            selected_assets_data,
            scored_results_data or {},
        ),
        "generated_at": generated_at or utc_now_iso(),
        "resolved_assets": resolved_assets,
        "summary": build_summary(resolved_assets),
    }


def resolve_scene(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    selected_asset: dict[str, Any] | None,
    resolution_choice: dict[str, Any] | None,
    scored_scene: dict[str, Any],
) -> dict[str, Any]:
    scene_number = int_or_zero(scene.get("scene"))
    asset_type = get_asset_type(visual_plan, selected_asset)

    if resolution_choice:
        return resolve_scene_choice(
            scene=scene,
            visual_plan=visual_plan,
            selected_asset=selected_asset,
            resolution_choice=resolution_choice,
            scored_scene=scored_scene,
            asset_type=asset_type,
        )

    if selected_asset:
        return resolve_selected_asset(
            scene=scene,
            visual_plan=visual_plan,
            selected_asset=selected_asset,
            asset_type=asset_type,
        )

    return build_missing_resolution(
        scene=scene,
        visual_plan=visual_plan,
        asset_type=asset_type,
    )


def resolve_scene_choice(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    selected_asset: dict[str, Any] | None,
    resolution_choice: dict[str, Any],
    scored_scene: dict[str, Any],
    asset_type: str,
) -> dict[str, Any]:
    resolution_type = clean_string(resolution_choice.get("resolution_type"))
    validate_resolution_type(resolution_type)

    if resolution_type == "placeholder":
        return build_base_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            resolution_type="placeholder",
            status="placeholder",
            message=clean_string(resolution_choice.get("message"))
            or "Usar placeholder hasta resolver esta escena.",
            selected_clip=None,
        )

    if resolution_type == "fallback_stock":
        return build_fallback_stock_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            resolution_choice=resolution_choice,
            scored_scene=scored_scene,
        )

    if resolution_type == "missing_asset":
        return build_missing_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            message=clean_string(resolution_choice.get("message")),
        )

    if resolution_type in {"pexels", "local"} and selected_asset:
        return resolve_selected_asset(
            scene=scene,
            visual_plan=visual_plan,
            selected_asset=selected_asset,
            asset_type=asset_type,
        )

    return build_missing_resolution(
        scene=scene,
        visual_plan=visual_plan,
        asset_type=asset_type,
        message=(
            clean_string(resolution_choice.get("message"))
            or f"Resolución {resolution_type} solicitada, pero no hay asset seleccionado."
        ),
    )


def resolve_selected_asset(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    selected_asset: dict[str, Any],
    asset_type: str,
) -> dict[str, Any]:
    selection_type = clean_string(selected_asset.get("selection_type"))
    selected_clip = selected_asset.get("selected_clip") or None
    provider = clean_string((selected_clip or {}).get("provider"))

    if selection_type == "manual_task":
        return build_missing_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            message=get_manual_task_message(selected_asset, scene, visual_plan),
        )

    if selection_type == "local" or provider == "local":
        return build_base_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            resolution_type="local",
            status="ready",
            message="Asset local seleccionado.",
            selected_clip=selected_clip,
        )

    if selection_type == "pexels" or provider == "pexels":
        return build_base_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            resolution_type="pexels",
            status="ready",
            message="Clip Pexels seleccionado.",
            selected_clip=selected_clip,
        )

    return build_missing_resolution(
        scene=scene,
        visual_plan=visual_plan,
        asset_type=asset_type,
        message="Selección no reconocida. Revisión manual requerida.",
        status="needs_manual_review",
    )


def build_fallback_stock_resolution(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    asset_type: str,
    resolution_choice: dict[str, Any],
    scored_scene: dict[str, Any],
) -> dict[str, Any]:
    best_suggestion = get_best_suggestion(scored_scene)

    if best_suggestion:
        return build_base_resolution(
            scene=scene,
            visual_plan=visual_plan,
            asset_type=asset_type,
            resolution_type="fallback_stock",
            status="fallback_stock",
            message=clean_string(resolution_choice.get("message"))
            or "Usar stock de relleno existente.",
            selected_clip=best_suggestion,
        )

    return build_base_resolution(
        scene=scene,
        visual_plan=visual_plan,
        asset_type=asset_type,
        resolution_type="fallback_stock",
        status="needs_fallback_search",
        message=clean_string(resolution_choice.get("message"))
        or "Se necesita buscar stock de relleno para esta escena.",
        selected_clip=None,
    )


def build_missing_resolution(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    asset_type: str,
    message: str = "",
    status: str | None = None,
) -> dict[str, Any]:
    resolved_status = status or get_missing_status(asset_type)

    return build_base_resolution(
        scene=scene,
        visual_plan=visual_plan,
        asset_type=asset_type,
        resolution_type="missing_asset",
        status=resolved_status,
        message=message or get_missing_message(asset_type, scene, visual_plan),
        selected_clip=None,
    )


def build_base_resolution(
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    asset_type: str,
    resolution_type: str,
    status: str,
    message: str,
    selected_clip: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "scene": int_or_zero(scene.get("scene")),
        "asset_type": asset_type,
        "resolution_type": resolution_type,
        "status": status,
        "message": message,
        "primary_action": visual_plan.get("primary_action") or scene.get("visual", ""),
        "visual_intent": visual_plan.get("visual_intent") or scene.get("text_on_screen", ""),
        "query": visual_plan.get("search_query_en", ""),
        "selected_clip": selected_clip,
    }


def get_best_suggestion(scored_scene: dict[str, Any]) -> dict[str, Any] | None:
    suggestions = scored_scene.get("suggestions", [])

    if not suggestions:
        return None

    return max(suggestions, key=lambda suggestion: int_or_zero(suggestion.get("score")))


def get_missing_status(asset_type: str) -> str:
    if asset_type == "self_recorded":
        return "needs_self_recording"

    if asset_type == "screen_recording":
        return "needs_screen_recording"

    if asset_type in {"stock", "mixed"}:
        return "missing_asset"

    return "needs_manual_review"


def get_missing_message(
    asset_type: str,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
) -> str:
    action = visual_plan.get("primary_action") or scene.get("visual", "")

    if asset_type == "self_recorded":
        return f"Grabar al creador en cámara. {action}".strip()

    if asset_type == "screen_recording":
        return f"Grabar pantalla o interfaz. {action}".strip()

    if asset_type in {"stock", "mixed"}:
        return "Escena sin asset seleccionado. Requiere selección manual, fallback stock o placeholder."

    return "Escena pendiente de revisión manual."


def get_manual_task_message(
    selected_asset: dict[str, Any],
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
) -> str:
    manual_task = selected_asset.get("manual_task", {})
    return (
        clean_string(manual_task.get("primary_action"))
        or clean_string(visual_plan.get("primary_action"))
        or clean_string(scene.get("visual"))
        or "Tarea manual pendiente."
    )


def get_asset_type(
    visual_plan: dict[str, Any],
    selected_asset: dict[str, Any] | None,
) -> str:
    if selected_asset:
        asset_type = clean_string(selected_asset.get("asset_type"))
        if asset_type:
            return asset_type

    return clean_string(visual_plan.get("asset_type")) or "unknown"


def build_summary(resolved_assets: list[dict[str, Any]]) -> dict[str, int]:
    ready_count = sum(
        1 for item in resolved_assets if item.get("status") in READY_STATUSES
    )
    pending_count = len(resolved_assets) - ready_count

    return {
        "scene_count": len(resolved_assets),
        "ready_count": ready_count,
        "pending_count": pending_count,
    }


def validate_resolution_type(resolution_type: str) -> None:
    if resolution_type not in ALLOWED_RESOLUTION_TYPES:
        allowed = ", ".join(sorted(ALLOWED_RESOLUTION_TYPES))
        raise ValueError(
            f"resolution_type no soportado: {resolution_type or '(vacío)'}. "
            f"Usa uno de: {allowed}."
        )


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
