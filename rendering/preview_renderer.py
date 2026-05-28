from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


Runner = Callable[[list[str]], None]
DurationReader = Callable[[Path], float]
DURATION_TOLERANCE_SECONDS = 0.25
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 24


def render_preview_video(
    *,
    timeline_data: dict[str, Any],
    prepared_clips_dir: Path,
    placeholders_dir: Path,
    output_path: Path,
    temp_dir: Path,
    concat_list_path: Path,
    manifest_path: Path,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
    runner: Runner | None = None,
    duration_reader: DurationReader | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    resolved_ffmpeg_path = resolve_tool_path(
        tool_name="ffmpeg",
        provided_path=ffmpeg_path,
        install_message="Instala ffmpeg antes de renderizar el video preliminar.",
    )
    resolved_ffprobe_path = resolve_ffprobe_path(ffprobe_path, duration_reader)
    command_runner = runner or run_subprocess
    read_duration = duration_reader or build_ffprobe_duration_reader(resolved_ffprobe_path)

    timeline_items = sorted_timeline_items(timeline_data.get("timeline", []))

    if not timeline_items:
        raise ValueError("data/timeline.json no tiene escenas para renderizar.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    render_items = []
    warnings = []
    normalized_paths = []

    for timeline_item in timeline_items:
        source_path, strategy, warning = find_source_path(
            timeline_item=timeline_item,
            prepared_clips_dir=prepared_clips_dir,
            placeholders_dir=placeholders_dir,
        )

        if warning:
            warnings.append(warning)

        duration_seconds = get_target_duration(timeline_item)
        source_duration = read_duration(source_path)

        validate_source_duration(
            timeline_item=timeline_item,
            source_path=source_path,
            source_duration=source_duration,
            target_duration=duration_seconds,
        )

        normalized_path = temp_dir / build_normalized_filename(
            int_or_zero(timeline_item.get("scene"))
        )
        normalize_clip(
            ffmpeg_path=resolved_ffmpeg_path,
            source_path=source_path,
            output_path=normalized_path,
            duration_seconds=duration_seconds,
            runner=command_runner,
        )

        normalized_paths.append(normalized_path)
        render_items.append(
            build_manifest_timeline_item(
                timeline_item=timeline_item,
                source_path=source_path,
                normalized_path=normalized_path,
                duration_seconds=duration_seconds,
                source_duration_seconds=source_duration,
                strategy=strategy,
            )
        )

    write_concat_list(concat_list_path, normalized_paths)
    concatenate_clips(
        ffmpeg_path=resolved_ffmpeg_path,
        concat_list_path=concat_list_path,
        output_path=output_path,
        runner=command_runner,
    )

    manifest = {
        "project_title": clean_string(timeline_data.get("project_title"))
        or "Proyecto sin título",
        "generated_at": generated_at or utc_now_iso(),
        "output_path": str(output_path),
        "timeline": render_items,
        "warnings": warnings,
        "summary": build_summary(
            timeline_items=timeline_items,
            render_items=render_items,
            warnings=warnings,
        ),
    }

    write_manifest(manifest_path, manifest)
    return manifest


def find_source_path(
    *,
    timeline_item: dict[str, Any],
    prepared_clips_dir: Path,
    placeholders_dir: Path,
) -> tuple[Path, str, dict[str, Any] | None]:
    scene_number = int_or_zero(timeline_item.get("scene"))
    prepared_path = prepared_clips_dir / build_ready_filename(scene_number)
    placeholder_path = placeholders_dir / build_placeholder_filename(scene_number)

    if prepared_path.exists():
        return prepared_path, "prepared_clip", None

    if placeholder_path.exists():
        return (
            placeholder_path,
            "placeholder_fallback",
            build_warning(
                timeline_item=timeline_item,
                reason=(
                    "No existe clip preparado para la escena; "
                    "se usó placeholder como respaldo."
                ),
                strategy="placeholder_fallback",
                source_path=placeholder_path,
            ),
        )

    raise RuntimeError(
        f"No existe clip preparado ni placeholder para la escena {scene_number}. "
        "Ejecuta python3 main.py prepare o python3 main.py placeholders antes de render."
    )


def normalize_clip(
    *,
    ffmpeg_path: str,
    source_path: Path,
    output_path: Path,
    duration_seconds: float,
    runner: Runner,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    runner(
        build_ffmpeg_normalize_command(
            ffmpeg_path=ffmpeg_path,
            source_path=source_path,
            output_path=output_path,
            duration_seconds=duration_seconds,
        )
    )


def concatenate_clips(
    *,
    ffmpeg_path: str,
    concat_list_path: Path,
    output_path: Path,
    runner: Runner,
) -> None:
    runner(
        build_ffmpeg_concat_command(
            ffmpeg_path=ffmpeg_path,
            concat_list_path=concat_list_path,
            output_path=output_path,
        )
    )


def build_ffmpeg_normalize_command(
    *,
    ffmpeg_path: str,
    source_path: Path,
    output_path: Path,
    duration_seconds: float,
) -> list[str]:
    video_filter = (
        f"scale={DEFAULT_WIDTH}:{DEFAULT_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={DEFAULT_WIDTH}:{DEFAULT_HEIGHT},"
        f"fps={DEFAULT_FPS},setsar=1"
    )

    return [
        ffmpeg_path,
        "-y",
        "-i",
        str(source_path),
        "-t",
        format_duration_for_ffmpeg(duration_seconds),
        "-vf",
        video_filter,
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def build_ffmpeg_concat_command(
    *,
    ffmpeg_path: str,
    concat_list_path: Path,
    output_path: Path,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list_path),
        "-c",
        "copy",
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
            "No se encontró ffmpeg. Instálalo antes de renderizar el video preliminar."
        ) from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        detail = f" Detalle: {stderr}" if stderr else ""
        raise RuntimeError(f"ffmpeg no pudo renderizar el video preliminar.{detail}") from error


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
                "No se encontró ffprobe. Instálalo antes de renderizar el video preliminar."
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


def validate_source_duration(
    *,
    timeline_item: dict[str, Any],
    source_path: Path,
    source_duration: float,
    target_duration: float,
) -> None:
    if source_duration <= 0:
        raise RuntimeError(f"La fuente {source_path} no tiene duración válida.")

    if source_duration < target_duration - DURATION_TOLERANCE_SECONDS:
        scene_number = int_or_zero(timeline_item.get("scene"))
        raise RuntimeError(
            f"La escena {scene_number} necesita {format_duration_for_message(target_duration)}s, "
            f"pero {source_path} dura {format_duration_for_message(source_duration)}s. "
            "Ejecuta python3 main.py prepare y revisa warnings antes de render."
        )


def write_concat_list(path: Path, clip_paths: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"file '{escape_concat_path(clip_path.resolve())}'" for clip_path in clip_paths]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def build_manifest_timeline_item(
    *,
    timeline_item: dict[str, Any],
    source_path: Path,
    normalized_path: Path,
    duration_seconds: float,
    source_duration_seconds: float,
    strategy: str,
) -> dict[str, Any]:
    return {
        "scene": int_or_zero(timeline_item.get("scene")),
        "source_path": str(source_path),
        "normalized_path": str(normalized_path),
        "duration_seconds": normalize_number(duration_seconds),
        "source_duration_seconds": round(source_duration_seconds, 3),
        "status": clean_string(timeline_item.get("status")) or "ready",
        "strategy": strategy,
    }


def build_warning(
    *,
    timeline_item: dict[str, Any],
    reason: str,
    strategy: str,
    source_path: Path | None = None,
) -> dict[str, Any]:
    warning = {
        "scene": int_or_zero(timeline_item.get("scene")),
        "status": "warning",
        "strategy": strategy,
        "reason": reason,
        "duration_seconds": normalize_number(get_target_duration(timeline_item)),
    }

    if source_path is not None:
        warning["source_path"] = str(source_path)

    return warning


def build_summary(
    *,
    timeline_items: list[dict[str, Any]],
    render_items: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, int | float]:
    return {
        "scene_count": len(timeline_items),
        "rendered_scene_count": len(render_items),
        "warning_count": len(warnings),
        "total_duration_seconds": normalize_number(
            sum(float_or_zero(item.get("duration_seconds")) for item in timeline_items)
        ),
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_target_duration(timeline_item: dict[str, Any]) -> float:
    duration = float_or_zero(timeline_item.get("duration_seconds"))

    if duration <= 0:
        scene_number = timeline_item.get("scene", "desconocida")
        raise ValueError(
            f"La escena {scene_number} no tiene duration_seconds válido para render."
        )

    return duration


def build_ready_filename(scene_number: int) -> str:
    return f"scene_{scene_number:02d}_ready.mp4"


def build_placeholder_filename(scene_number: int) -> str:
    return f"scene_{scene_number:02d}_placeholder.mp4"


def build_normalized_filename(scene_number: int) -> str:
    return f"scene_{scene_number:02d}_normalized.mp4"


def resolve_ffprobe_path(
    ffprobe_path: str | None,
    duration_reader: DurationReader | None,
) -> str:
    if duration_reader is not None:
        return clean_string(ffprobe_path) or "ffprobe"

    return resolve_tool_path(
        tool_name="ffprobe",
        provided_path=ffprobe_path,
        install_message="Instala ffprobe antes de renderizar el video preliminar.",
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def format_duration_for_ffmpeg(duration_seconds: float) -> str:
    if float(duration_seconds).is_integer():
        return str(int(duration_seconds))

    return f"{duration_seconds:.3f}".rstrip("0").rstrip(".")


def format_duration_for_message(duration_seconds: float) -> str:
    return str(normalize_number(duration_seconds))


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
