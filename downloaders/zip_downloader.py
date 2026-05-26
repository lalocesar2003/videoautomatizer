import json
import shutil
import ssl
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


Fetcher = Callable[[str], bytes]
SUPPORTED_LOCAL_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}


def export_selected_assets(
    *,
    selected_assets_path: Path,
    clips_dir: Path,
    zip_path: Path,
    fetcher: Fetcher | None = None,
) -> dict[str, Any]:
    selected_assets = load_selected_assets(selected_assets_path)
    selected_items = selected_assets.get("selected_assets", [])

    if not selected_items:
        raise ValueError("data/selected_assets.json no contiene clips seleccionados.")

    clips_dir.mkdir(parents=True, exist_ok=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    fetch = fetcher or fetch_url
    project_root = selected_assets_path.resolve().parent.parent
    downloaded_clips = download_selected_clips(
        selected_items,
        clips_dir,
        fetch,
        project_root=project_root,
    )

    if not downloaded_clips:
        raise ValueError(
            "data/selected_assets.json no contiene assets exportables."
        )

    create_selected_zip(
        zip_path=zip_path,
        selected_assets_path=selected_assets_path,
        downloaded_clips=downloaded_clips,
    )

    return {
        "downloaded_count": len(downloaded_clips),
        "clips_dir": str(clips_dir),
        "zip_path": str(zip_path),
        "files": [str(path) for path in downloaded_clips],
    }


def load_selected_assets(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Guarda una selección desde el panel Streamlit primero."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def download_selected_clips(
    selected_items: list[dict[str, Any]],
    clips_dir: Path,
    fetcher: Fetcher,
    *,
    project_root: Path | None = None,
) -> list[Path]:
    downloaded = []
    scene_counts: dict[int, int] = defaultdict(int)
    project_root = project_root or Path(".").resolve()

    for item in selected_items:
        scene_number = int_or_zero(item.get("scene"))
        selection_type = clean_string(item.get("selection_type"))

        if selection_type == "manual_task":
            continue

        selected_clip = item.get("selected_clip", {})
        provider = clean_string(selected_clip.get("provider"))

        if selection_type == "local" or provider == "local":
            scene_counts[scene_number] += 1
            output_path = copy_local_clip(
                selected_clip=selected_clip,
                scene_number=scene_number,
                clip_number=scene_counts[scene_number],
                clips_dir=clips_dir,
                project_root=project_root,
            )
            downloaded.append(output_path)
            continue

        preview_url = clean_string(selected_clip.get("preview_url"))

        if not preview_url:
            raise ValueError(
                f"La escena {scene_number} tiene un clip seleccionado sin preview_url."
            )

        scene_counts[scene_number] += 1
        filename = build_clip_filename(scene_number, scene_counts[scene_number])
        output_path = clips_dir / filename

        try:
            output_path.write_bytes(fetcher(preview_url))
        except Exception as error:
            raise RuntimeError(
                f"No se pudo descargar el clip de la escena {scene_number}: {preview_url}"
            ) from error

        downloaded.append(output_path)

    return downloaded


def copy_local_clip(
    *,
    selected_clip: dict[str, Any],
    scene_number: int,
    clip_number: int,
    clips_dir: Path,
    project_root: Path,
) -> Path:
    local_path = clean_string(selected_clip.get("local_path"))

    if not local_path:
        raise ValueError(
            f"La escena {scene_number} tiene un asset local sin local_path."
        )

    source_path = resolve_local_path(local_path, project_root)
    validate_local_video_path(source_path, scene_number)

    filename = build_clip_filename(
        scene_number,
        clip_number,
        extension=source_path.suffix.lower(),
    )
    output_path = clips_dir / filename

    try:
        shutil.copy2(source_path, output_path)
    except Exception as error:
        raise RuntimeError(
            f"No se pudo copiar el asset local de la escena {scene_number}: {source_path}"
        ) from error

    return output_path


def resolve_local_path(local_path: str, project_root: Path) -> Path:
    path = Path(local_path)

    if path.is_absolute():
        return path

    return project_root / path


def validate_local_video_path(path: Path, scene_number: int) -> None:
    extension = path.suffix.lower()

    if extension not in SUPPORTED_LOCAL_VIDEO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_LOCAL_VIDEO_EXTENSIONS))
        raise ValueError(
            f"La escena {scene_number} usa un asset local con extensión no soportada: "
            f"{extension or '(vacía)'}. Usa una de estas: {supported}."
        )

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el asset local de la escena {scene_number}: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"El asset local de la escena {scene_number} no es un archivo: {path}"
        )


def create_selected_zip(
    *,
    zip_path: Path,
    selected_assets_path: Path,
    downloaded_clips: list[Path],
) -> None:
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(selected_assets_path, arcname="selected_assets.json")

        for clip_path in downloaded_clips:
            archive.write(clip_path, arcname=f"clips/{clip_path.name}")


def build_clip_filename(
    scene_number: int,
    clip_number: int,
    extension: str = ".mp4",
) -> str:
    return f"scene_{scene_number:02d}_clip_{clip_number:02d}{extension}"


def fetch_url(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "videosstock-exporter/1.0"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=60, context=build_ssl_context()) as response:
            return response.read()
    except URLError as error:
        raise RuntimeError(f"No se pudo descargar {url}") from error


def build_ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
    except ModuleNotFoundError:
        return None

    return ssl.create_default_context(cafile=certifi.where())


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)


def clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
