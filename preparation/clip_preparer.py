from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


Runner = Callable[[list[str]], None]
DurationReader = Callable[[Path], float]
DURATION_TOLERANCE_SECONDS = 0.20


def prepare_clips(
    *,
    timeline_data: dict[str, Any],
    clips_dir: Path,
    placeholders_dir: Path,
    output_dir: Path,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
    runner: Runner | None = None,
    duration_reader: DurationReader | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    resolved_ffmpeg_path = resolve_tool_path(
        tool_name="ffmpeg",
        provided_path=ffmpeg_path,
        install_message="Instala ffmpeg antes de preparar clips.",
    )
    resolved_ffprobe_path = resolve_ffprobe_path(ffprobe_path, duration_reader)
    command_runner = runner or run_subprocess
    read_duration = duration_reader or build_ffprobe_duration_reader(resolved_ffprobe_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    prepared_clips = []
    warnings = []

    for timeline_item in sorted_timeline_items(timeline_data.get("timeline", [])):
        prepared_item, item_warnings = prepare_timeline_item(
            timeline_item=timeline_item,
            clips_dir=clips_dir,
            placeholders_dir=placeholders_dir,
            output_dir=output_dir,
            ffmpeg_path=resolved_ffmpeg_path,
            runner=command_runner,
            duration_reader=read_duration,
        )
        warnings.extend(item_warnings)

        if prepared_item:
            prepared_clips.append(prepared_item)

    manifest = {
        "project_title": clean_string(timeline_data.get("project_title"))
        or "Proyecto sin título",
        "generated_at": generated_at or utc_now_iso(),
        "prepared_clips": prepared_clips,
        "warnings": warnings,
        "summary": build_summary(
            timeline_items=timeline_data.get("timeline", []),
            prepared_clips=prepared_clips,
            warnings=warnings,
        ),
    }

    write_manifest(output_dir / "prepared_manifest.json", manifest)
    return manifest


def prepare_timeline_item(
    *,
    timeline_item: dict[str, Any],
    clips_dir: Path,
    placeholders_dir: Path,
    output_dir: Path,
    ffmpeg_path: str,
    runner: Runner,
    duration_reader: DurationReader,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    scene_number = int_or_zero(timeline_item.get("scene"))
    target_duration = get_target_duration(timeline_item)
    output_path = output_dir / build_ready_filename(scene_number)
    warnings = []

    source_path, source_kind, source_warning = find_source_path(
        timeline_item=timeline_item,
        clips_dir=clips_dir,
        placeholders_dir=placeholders_dir,
    )

    if source_warning:
        warnings.append(source_warning)

    if source_path is None:
        warnings.append(
            build_warning(
                timeline_item=timeline_item,
                reason="No existe clip real ni placeholder para preparar esta escena.",
                strategy="manual_review",
            )
        )
        return None, warnings

    source_duration = duration_reader(source_path)

    if source_duration <= 0:
        warnings.append(
            build_warning(
                timeline_item=timeline_item,
                reason=f"No se pudo obtener una duración válida para {source_path}.",
                strategy="manual_review",
                source_path=source_path,
            )
        )
        return None, warnings

    if source_duration < target_duration - DURATION_TOLERANCE_SECONDS:
        placeholder_path = build_placeholder_path(placeholders_dir, scene_number)

        if source_kind != "placeholder" and placeholder_path.exists():
            warnings.append(
                build_warning(
                    timeline_item=timeline_item,
                    reason=(
                        "El clip fuente es más corto que la duración objetivo; "
                        "se usó placeholder como respaldo."
                    ),
                    strategy="placeholder",
                    source_path=source_path,
                    source_duration_seconds=source_duration,
                )
            )
            source_path = placeholder_path
            source_kind = "placeholder"
            source_duration = duration_reader(source_path)
        else:
            warnings.append(
                build_warning(
                    timeline_item=timeline_item,
                    reason=(
                        "El clip fuente es más corto que la duración objetivo "
                        "y no hay placeholder utilizable."
                    ),
                    strategy="manual_review",
                    source_path=source_path,
                    source_duration_seconds=source_duration,
                )
            )
            return None, warnings

    if source_duration < target_duration - DURATION_TOLERANCE_SECONDS:
        warnings.append(
            build_warning(
                timeline_item=timeline_item,
                reason=(
                    "El placeholder también es más corto que la duración objetivo. "
                    "Requiere revisión manual."
                ),
                strategy="manual_review",
                source_path=source_path,
                source_duration_seconds=source_duration,
            )
        )
        return None, warnings

    strategy = choose_strategy(
        source_kind=source_kind,
        source_duration=source_duration,
        target_duration=target_duration,
    )

    create_prepared_clip(
        ffmpeg_path=ffmpeg_path,
        source_path=source_path,
        output_path=output_path,
        duration_seconds=target_duration,
        runner=runner,
    )

    return (
        build_manifest_item(
            timeline_item=timeline_item,
            source_path=source_path,
            output_path=output_path,
            duration_seconds=target_duration,
            source_duration_seconds=source_duration,
            strategy=strategy,
        ),
        warnings,
    )


def find_source_path(
    *,
    timeline_item: dict[str, Any],
    clips_dir: Path,
    placeholders_dir: Path,
) -> tuple[Path | None, str, dict[str, Any] | None]:
    scene_number = int_or_zero(timeline_item.get("scene"))
    clip_path = clean_string(timeline_item.get("clip_path"))
    placeholder_path = build_placeholder_path(placeholders_dir, scene_number)

    if clip_path:
        resolved_clip_path = resolve_clip_path(clip_path, clips_dir)

        if resolved_clip_path.exists():
            return resolved_clip_path, "clip", None

        if placeholder_path.exists():
            return (
                placeholder_path,
                "placeholder",
                build_warning(
                    timeline_item=timeline_item,
                    reason=(
                        "El clip_path del timeline no existe en disco; "
                        "se usó placeholder como respaldo."
                    ),
                    strategy="placeholder",
                    source_path=resolved_clip_path,
                ),
            )

        return None, "missing", build_warning(
            timeline_item=timeline_item,
            reason="El clip_path del timeline no existe en disco.",
            strategy="manual_review",
            source_path=resolved_clip_path,
        )

    if placeholder_path.exists():
        return placeholder_path, "placeholder", None

    return None, "missing", None


def create_prepared_clip(
    *,
    ffmpeg_path: str,
    source_path: Path,
    output_path: Path,
    duration_seconds: float,
    runner: Runner,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_prepare_command(
        ffmpeg_path=ffmpeg_path,
        source_path=source_path,
        output_path=output_path,
        duration_seconds=duration_seconds,
    )
    runner(command)


def build_ffmpeg_prepare_command(
    *,
    ffmpeg_path: str,
    source_path: Path,
    output_path: Path,
    duration_seconds: float,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-i",
        str(source_path),
        "-t",
        format_duration_for_ffmpeg(duration_seconds),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def run_subprocess(command: list[str]) -> None:
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "No se encontró ffmpeg. Instálalo antes de preparar clips."
        ) from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        detail = f" Detalle: {stderr}" if stderr else ""
        raise RuntimeError(f"ffmpeg no pudo preparar el clip.{detail}") from error


def build_ffprobe_duration_reader(ffprobe_path: str) -> DurationReader:
    def read_duration(path: Path) -> float:
        command = [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                "No se encontró ffprobe. Instálalo antes de preparar clips."
            ) from error
        except subprocess.CalledProcessError as error:
            stderr = (error.stderr or "").strip()
            detail = f" Detalle: {stderr}" if stderr else ""
            raise RuntimeError(f"ffprobe no pudo leer la duración de {path}.{detail}") from error

        raw_duration = result.stdout.strip()

        try:
            return float(raw_duration)
        except ValueError as error:
            raise RuntimeError(
                f"ffprobe devolvió una duración inválida para {path}: {raw_duration}"
            ) from error

    return read_duration


def build_manifest_item(
    *,
    timeline_item: dict[str, Any],
    source_path: Path,
    output_path: Path,
    duration_seconds: float,
    source_duration_seconds: float,
    strategy: str,
) -> dict[str, Any]:
    return {
        "scene": int_or_zero(timeline_item.get("scene")),
        "status": "ready",
        "source_path": str(source_path),
        "output_path": str(output_path),
        "duration_seconds": normalize_number(duration_seconds),
        "source_duration_seconds": round(source_duration_seconds, 3),
        "strategy": strategy,
        "asset_type": clean_string(timeline_item.get("asset_type")),
        "timeline_status": clean_string(timeline_item.get("status")),
    }


def build_warning(
    *,
    timeline_item: dict[str, Any],
    reason: str,
    strategy: str,
    source_path: Path | None = None,
    source_duration_seconds: float | None = None,
) -> dict[str, Any]:
    warning = {
        "scene": int_or_zero(timeline_item.get("scene")),
        "status": "needs_manual_review" if strategy == "manual_review" else "warning",
        "strategy": strategy,
        "reason": reason,
        "duration_seconds": normalize_number(get_target_duration(timeline_item)),
        "asset_type": clean_string(timeline_item.get("asset_type")),
        "timeline_status": clean_string(timeline_item.get("status")),
    }

    if source_path is not None:
        warning["source_path"] = str(source_path)

    if source_duration_seconds is not None:
        warning["source_duration_seconds"] = round(source_duration_seconds, 3)

    return warning


def choose_strategy(
    *,
    source_kind: str,
    source_duration: float,
    target_duration: float,
) -> str:
    if source_kind == "placeholder":
        return "placeholder"

    if source_duration > target_duration + DURATION_TOLERANCE_SECONDS:
        return "trim"

    return "copy"


def get_target_duration(timeline_item: dict[str, Any]) -> float:
    duration = float_or_zero(timeline_item.get("duration_seconds"))

    if duration <= 0:
        scene_number = timeline_item.get("scene", "desconocida")
        raise ValueError(
            f"La escena {scene_number} no tiene duration_seconds válido para preparar clip."
        )

    return duration


def build_ready_filename(scene_number: int) -> str:
    return f"scene_{scene_number:02d}_ready.mp4"


def build_placeholder_path(placeholders_dir: Path, scene_number: int) -> Path:
    return placeholders_dir / f"scene_{scene_number:02d}_placeholder.mp4"


def resolve_clip_path(clip_path: str, clips_dir: Path) -> Path:
    path = Path(clip_path)

    if path.is_absolute():
        return path

    if path.exists():
        return path

    return clips_dir / path.name


def resolve_ffprobe_path(
    ffprobe_path: str | None,
    duration_reader: DurationReader | None,
) -> str:
    if duration_reader is not None:
        return clean_string(ffprobe_path) or "ffprobe"

    return resolve_tool_path(
        tool_name="ffprobe",
        provided_path=ffprobe_path,
        install_message="Instala ffprobe antes de preparar clips.",
    )


def resolve_tool_path(
    *,
    tool_name: str,
    provided_path: str | None,
    install_message: str,
) -> str:
    if provided_path is not None:
        resolved = clean_string(provided_path)
    else:
        resolved = shutil.which(tool_name) or ""

    if not resolved:
        raise RuntimeError(f"No se encontró {tool_name}. {install_message}")

    return resolved


def sorted_timeline_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: int_or_zero(item.get("scene")))


def build_summary(
    *,
    timeline_items: list[dict[str, Any]],
    prepared_clips: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, int | float]:
    return {
        "scene_count": len(timeline_items),
        "prepared_count": len(prepared_clips),
        "warning_count": len(warnings),
        "total_duration_seconds": normalize_number(
            sum(float_or_zero(item.get("duration_seconds")) for item in timeline_items)
        ),
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def format_duration_for_ffmpeg(duration_seconds: float) -> str:
    if float(duration_seconds).is_integer():
        return str(int(duration_seconds))

    return f"{duration_seconds:.3f}".rstrip("0").rstrip(".")


def normalize_number(value: float) -> int | float:
    number = float(value)

    if number.is_integer():
        return int(number)

    return round(number, 3)


def clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
