from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MISSING_STATUSES = {
    "needs_self_recording",
    "needs_screen_recording",
    "needs_manual_review",
    "needs_fallback_search",
    "missing_asset",
}
READY_FILE_STATUSES = {"ready", "fallback_stock"}

REASON_BY_STATUS = {
    "needs_self_recording": (
        "La escena requiere grabación del creador y no tiene asset local listo.",
        "Grabar al creador o asignar un video local desde el panel.",
    ),
    "needs_screen_recording": (
        "La escena requiere una grabación de pantalla y no tiene asset listo.",
        "Grabar pantalla o asignar un video local desde el panel.",
    ),
    "needs_fallback_search": (
        "La escena necesita stock de relleno, pero todavía no tiene sugerencias disponibles.",
        "Ejecutar una búsqueda fallback en una fase posterior o marcar placeholder.",
    ),
    "missing_asset": (
        "La escena no tiene asset seleccionado ni resolución lista para render.",
        "Seleccionar Pexels, asignar video local, usar fallback stock o marcar placeholder.",
    ),
    "needs_manual_review": (
        "La escena requiere revisión manual antes del render.",
        "Revisar la escena y elegir una resolución válida.",
    ),
}

BROKEN_ASSET_REASON = (
    "La escena fue marcada como lista, pero el archivo indicado en clip_path no existe.",
    "Ejecutar export, corregir clip_path o volver a seleccionar el asset.",
)

EMPTY_CLIP_PATH_REASON = (
    "La escena fue marcada como lista, pero clip_path está vacío.",
    "Ejecutar export, corregir clip_path o volver a seleccionar el asset.",
)


def detect_missing_scenes(
    *,
    timeline_data: dict[str, Any],
    project_root: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    project_root = project_root or Path(".")
    missing_scenes = []

    for item in timeline_data.get("timeline", []):
        missing_scene = detect_missing_scene(item, project_root)

        if missing_scene:
            missing_scenes.append(missing_scene)

    return {
        "project_title": timeline_data.get("project_title", "Proyecto sin título"),
        "generated_at": generated_at or utc_now_iso(),
        "missing_scenes": missing_scenes,
        "summary": build_summary(missing_scenes),
    }


def detect_missing_scene(
    item: dict[str, Any],
    project_root: Path,
) -> dict[str, Any] | None:
    status = clean_string(item.get("status"))

    if status in MISSING_STATUSES:
        reason, suggested_action = REASON_BY_STATUS[status]
        return build_missing_scene(
            item=item,
            reason=reason,
            suggested_action=suggested_action,
            severity="blocking",
        )

    if status in READY_FILE_STATUSES:
        clip_path = clean_string(item.get("clip_path"))

        if not clip_path:
            reason, suggested_action = EMPTY_CLIP_PATH_REASON
            return build_missing_scene(
                item=item,
                reason=reason,
                suggested_action=suggested_action,
                severity="blocking",
            )

        if not resolve_clip_path(project_root, clip_path).is_file():
            reason, suggested_action = BROKEN_ASSET_REASON
            return build_missing_scene(
                item=item,
                reason=reason,
                suggested_action=suggested_action,
                severity="blocking",
            )

    return None


def build_missing_scene(
    *,
    item: dict[str, Any],
    reason: str,
    suggested_action: str,
    severity: str,
) -> dict[str, Any]:
    return {
        "scene": item.get("scene"),
        "start": item.get("start", ""),
        "end": item.get("end", ""),
        "duration_seconds": item.get("duration_seconds", 0),
        "asset_type": item.get("asset_type", ""),
        "resolution_type": item.get("resolution_type", ""),
        "status": item.get("status", ""),
        "severity": severity,
        "reason": reason,
        "primary_action": item.get("primary_action", ""),
        "suggested_action": suggested_action,
        "clip_path": item.get("clip_path"),
        "message": item.get("message", ""),
    }


def resolve_clip_path(project_root: Path, clip_path: str) -> Path:
    path = Path(clip_path)

    if path.is_absolute():
        return path

    return project_root / path


def build_summary(missing_scenes: list[dict[str, Any]]) -> dict[str, int]:
    blocking_count = sum(
        1 for item in missing_scenes if item.get("severity") == "blocking"
    )
    warning_count = sum(
        1 for item in missing_scenes if item.get("severity") == "warning"
    )

    return {
        "missing_count": len(missing_scenes),
        "blocking_count": blocking_count,
        "warning_count": warning_count,
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()
