from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


Runner = Callable[[list[str]], None]
DEFAULT_SIZE = "1080x1920"
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 24
DEFAULT_BACKGROUND = "0x111827"
BACKGROUND_RGB = (17, 24, 39)
FOREGROUND_RGB = (255, 255, 255)


def generate_placeholders(
    *,
    missing_scenes_data: dict[str, Any],
    timeline_data: dict[str, Any],
    output_dir: Path,
    ffmpeg_path: str | None = None,
    runner: Runner | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    resolved_ffmpeg_path = resolve_ffmpeg_path(ffmpeg_path)
    command_runner = runner or run_subprocess
    timeline_by_scene = index_by_scene(timeline_data.get("timeline", []))
    placeholders = []

    output_dir.mkdir(parents=True, exist_ok=True)

    for missing_scene in missing_scenes_data.get("missing_scenes", []):
        scene_number = int_or_zero(missing_scene.get("scene"))
        timeline_item = timeline_by_scene.get(scene_number, {})
        duration_seconds = get_duration_seconds(missing_scene, timeline_item)
        output_path = output_dir / build_placeholder_filename(scene_number)
        placeholder_text = build_placeholder_text(
            missing_scene=missing_scene,
            timeline_item=timeline_item,
            duration_seconds=duration_seconds,
        )

        create_placeholder_clip(
            ffmpeg_path=resolved_ffmpeg_path,
            output_path=output_path,
            placeholder_text=placeholder_text,
            duration_seconds=duration_seconds,
            runner=command_runner,
        )

        placeholders.append(
            build_manifest_item(
                missing_scene=missing_scene,
                timeline_item=timeline_item,
                output_path=output_path,
                duration_seconds=duration_seconds,
            )
        )

    manifest = {
        "project_title": get_project_title(missing_scenes_data, timeline_data),
        "generated_at": generated_at or utc_now_iso(),
        "placeholders": placeholders,
        "summary": build_summary(placeholders),
    }

    write_manifest(output_dir / "placeholder_manifest.json", manifest)
    return manifest


def create_placeholder_clip(
    *,
    ffmpeg_path: str,
    output_path: Path,
    placeholder_text: str,
    duration_seconds: int,
    runner: Runner,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_path = write_temporary_image(placeholder_text)

    try:
        command = build_ffmpeg_command(
            ffmpeg_path=ffmpeg_path,
            image_path=image_path,
            output_path=output_path,
            duration_seconds=duration_seconds,
        )
        runner(command)
    finally:
        image_path.unlink(missing_ok=True)


def build_ffmpeg_command(
    *,
    ffmpeg_path: str,
    image_path: Path,
    output_path: Path,
    duration_seconds: int,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-t",
        str(duration_seconds),
        "-r",
        str(DEFAULT_FPS),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
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
            "No se encontró ffmpeg. Instálalo antes de generar placeholders."
        ) from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        detail = f" Detalle: {stderr}" if stderr else ""
        raise RuntimeError(f"ffmpeg no pudo generar el placeholder.{detail}") from error


def build_placeholder_text(
    *,
    missing_scene: dict[str, Any],
    timeline_item: dict[str, Any],
    duration_seconds: int,
) -> str:
    scene_number = int_or_zero(missing_scene.get("scene"))
    asset_type = get_first_value(missing_scene, timeline_item, "asset_type")
    status = get_first_value(missing_scene, timeline_item, "status")
    primary_action = get_first_value(missing_scene, timeline_item, "primary_action")
    reason = get_first_value(missing_scene, timeline_item, "reason")

    action_lines = wrap_multiline(primary_action, width=28)
    reason_lines = wrap_multiline(reason, width=28)

    lines = [
        f"ESCENA {scene_number} FALTANTE",
        f"Tipo: {asset_type or 'desconocido'}",
        f"Estado: {status or 'pendiente'}",
        f"Duración: {duration_seconds} segundos",
        "",
        "Acción:",
        *action_lines,
    ]

    if reason_lines:
        lines.extend(["", "Motivo:", *reason_lines])

    return "\n".join(lines)


def build_manifest_item(
    *,
    missing_scene: dict[str, Any],
    timeline_item: dict[str, Any],
    output_path: Path,
    duration_seconds: int,
) -> dict[str, Any]:
    return {
        "scene": int_or_zero(missing_scene.get("scene")),
        "path": str(output_path),
        "duration_seconds": duration_seconds,
        "asset_type": get_first_value(missing_scene, timeline_item, "asset_type"),
        "status": get_first_value(missing_scene, timeline_item, "status"),
        "reason": get_first_value(missing_scene, timeline_item, "reason"),
        "primary_action": get_first_value(missing_scene, timeline_item, "primary_action"),
    }


def get_duration_seconds(
    missing_scene: dict[str, Any],
    timeline_item: dict[str, Any],
) -> int:
    duration = int_or_zero(
        missing_scene.get("duration_seconds") or timeline_item.get("duration_seconds")
    )

    if duration <= 0:
        scene_number = missing_scene.get("scene", "desconocida")
        raise ValueError(
            f"La escena {scene_number} no tiene duration_seconds válido para placeholder."
        )

    return duration


def build_placeholder_filename(scene_number: int) -> str:
    return f"scene_{scene_number:02d}_placeholder.mp4"


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_temporary_image(text: str) -> Path:
    with tempfile.NamedTemporaryFile(
        suffix=".ppm",
        delete=False,
    ) as file:
        path = Path(file.name)

    render_text_image(path=path, text=text)
    return path


def render_text_image(
    *,
    path: Path,
    text: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    scale: int = 6,
) -> None:
    pixels = bytearray(BACKGROUND_RGB * (width * height))
    normalized_lines = normalize_placeholder_text(text).splitlines()
    line_height = 8 * scale + 18
    total_text_height = len(normalized_lines) * line_height
    y = max((height - total_text_height) // 2, 80)

    for line in normalized_lines:
        draw_text_line(
            pixels=pixels,
            width=width,
            height=height,
            text=line,
            y=y,
            scale=scale,
        )
        y += line_height

    with path.open("wb") as file:
        file.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        file.write(pixels)


def draw_text_line(
    *,
    pixels: bytearray,
    width: int,
    height: int,
    text: str,
    y: int,
    scale: int,
) -> None:
    char_width = 5 * scale
    char_spacing = scale
    line_width = sum(
        get_character_width(character, scale) + char_spacing for character in text
    )
    x = max((width - line_width) // 2, 40)

    for character in text:
        pattern = FONT_5X7.get(character, FONT_5X7[" "])
        draw_character(
            pixels=pixels,
            width=width,
            height=height,
            pattern=pattern,
            x=x,
            y=y,
            scale=scale,
        )
        x += char_width + char_spacing


def draw_character(
    *,
    pixels: bytearray,
    width: int,
    height: int,
    pattern: list[str],
    x: int,
    y: int,
    scale: int,
) -> None:
    for row_index, row in enumerate(pattern):
        for column_index, value in enumerate(row):
            if value != "1":
                continue

            draw_block(
                pixels=pixels,
                width=width,
                height=height,
                x=x + column_index * scale,
                y=y + row_index * scale,
                scale=scale,
            )


def draw_block(
    *,
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    scale: int,
) -> None:
    for row in range(scale):
        pixel_y = y + row

        if pixel_y < 0 or pixel_y >= height:
            continue

        for column in range(scale):
            pixel_x = x + column

            if pixel_x < 0 or pixel_x >= width:
                continue

            index = (pixel_y * width + pixel_x) * 3
            pixels[index:index + 3] = bytes(FOREGROUND_RGB)


def get_character_width(character: str, scale: int) -> int:
    if character == " ":
        return 3 * scale

    return 5 * scale


def normalize_placeholder_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    allowed = []

    for character in ascii_text.upper():
        if character in FONT_5X7 or character == "\n":
            allowed.append(character)
        else:
            allowed.append(" ")

    return "".join(allowed)


def resolve_ffmpeg_path(ffmpeg_path: str | None) -> str:
    if ffmpeg_path is not None:
        resolved = clean_string(ffmpeg_path)
    else:
        resolved = shutil.which("ffmpeg") or ""

    if not resolved:
        raise RuntimeError(
            "No se encontró ffmpeg. Instálalo antes de generar placeholders."
        )

    return resolved


def wrap_multiline(value: str, width: int) -> list[str]:
    cleaned = clean_string(value)

    if not cleaned:
        return []

    wrapped = textwrap.wrap(cleaned, width=width)
    return wrapped or [cleaned]


def index_by_scene(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed = {}

    for item in items:
        scene_number = int_or_zero(item.get("scene"))

        if scene_number:
            indexed[scene_number] = item

    return indexed


def build_summary(placeholders: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "placeholder_count": len(placeholders),
        "total_duration_seconds": sum(
            int_or_zero(item.get("duration_seconds")) for item in placeholders
        ),
    }


def get_project_title(*sources: dict[str, Any]) -> str:
    for source in sources:
        title = clean_string(source.get("project_title"))
        if title:
            return title

    return "Proyecto sin título"


def get_first_value(*sources_and_key: Any) -> str:
    *sources, key = sources_and_key

    for source in sources:
        value = clean_string(source.get(key, ""))
        if value:
            return value

    return ""


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


FONT_5X7 = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
}
