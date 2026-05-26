from pathlib import Path
from typing import Any

from selection.asset_selector import (
    LOCAL_ASSET_CHOICE,
    SUPPORTED_VIDEO_EXTENSIONS,
    build_selected_assets_from_scene_choices,
    count_suggestions,
    get_choices_by_scene,
    get_local_assets_by_scene,
    load_json,
    save_selected_assets,
    save_uploaded_local_asset,
)


SCENES_PATH = Path("data/scenes.json")
VISUAL_PLAN_PATH = Path("data/visual_plan.json")
SCORED_RESULTS_PATH = Path("data/scored_results.json")
SELECTED_ASSETS_PATH = Path("data/selected_assets.json")
LOCAL_ASSETS_DIR = Path("local_assets")


def run_streamlit_panel(
    scenes_path: Path = SCENES_PATH,
    visual_plan_path: Path = VISUAL_PLAN_PATH,
    scored_results_path: Path = SCORED_RESULTS_PATH,
    selected_assets_path: Path = SELECTED_ASSETS_PATH,
) -> None:
    import streamlit as st

    st.set_page_config(
        page_title="B-roll selector",
        page_icon="🎬",
        layout="wide",
    )

    st.title("🎬 B-roll selector")
    st.caption("Revisa clips puntuados, abre previews y guarda tu selección manual.")

    scenes_data = load_json(scenes_path)
    visual_plan_data = load_json(visual_plan_path)
    scored_results = load_json(scored_results_path)
    previous_selection = load_previous_selection(selected_assets_path)
    previous_choices = get_choices_by_scene(previous_selection)
    previous_local_assets = get_local_assets_by_scene(previous_selection)

    scenes = scenes_data.get("scenes", [])
    visual_plan_by_scene = index_by_scene(visual_plan_data.get("visual_plan", []))
    scored_results_by_scene = index_by_scene(scored_results.get("results", []))

    st.write(f"**Proyecto:** {scored_results.get('project_title', 'Proyecto sin título')}")
    st.write(f"**Escenas:** {len(scenes)}")
    st.write(f"**Sugerencias:** {count_suggestions(scored_results)}")

    choices_by_scene, local_uploads_by_scene = render_scenes(
        scenes=scenes,
        visual_plan_by_scene=visual_plan_by_scene,
        scored_results_by_scene=scored_results_by_scene,
        previous_choices=previous_choices,
        previous_local_assets=previous_local_assets,
        st=st,
    )

    if st.button("Guardar selección", type="primary"):
        try:
            local_assets_by_scene = prepare_local_assets_for_selection(
                choices_by_scene=choices_by_scene,
                local_uploads_by_scene=local_uploads_by_scene,
                previous_local_assets=previous_local_assets,
            )
            selected_assets = build_selected_assets_from_scene_choices(
                project_title=scored_results.get("project_title", "Proyecto sin título"),
                scenes=scenes,
                visual_plan_by_scene=visual_plan_by_scene,
                scored_results_by_scene=scored_results_by_scene,
                choices_by_scene=choices_by_scene,
                local_assets_by_scene=local_assets_by_scene,
            )
        except ValueError as error:
            st.error(str(error))
            return

        save_selected_assets(selected_assets_path, selected_assets)
        st.success(
            f"Selección guardada en {selected_assets_path} "
            f"({len(selected_assets['selected_assets'])} clips)."
        )
        st.json(selected_assets)

    st.info("Fase 5A: no se descargan clips y no se genera ZIP todavía.")


def render_scenes(
    *,
    scenes: list[dict[str, Any]],
    visual_plan_by_scene: dict[int, dict[str, Any]],
    scored_results_by_scene: dict[int, dict[str, Any]],
    previous_choices: dict[int, str],
    previous_local_assets: dict[int, dict[str, Any]],
    st,
) -> tuple[dict[int, str], dict[int, Any]]:
    choices_by_scene = {}
    local_uploads_by_scene = {}

    for scene in scenes:
        scene_number = int(scene.get("scene", 0))
        visual_plan = visual_plan_by_scene.get(scene_number, {})
        scored_scene = scored_results_by_scene.get(scene_number, {})
        asset_type = visual_plan.get("asset_type", "")
        scene_title = f"Escena {scene_number} · {asset_type or 'sin clasificar'}"

        with st.expander(scene_title, expanded=True):
            st.write(f"**Tiempo:** {scene.get('start', '')} - {scene.get('end', '')}")
            st.write(f"**Sección:** {scene.get('section', '')}")
            st.write(f"**Visual original:** {scene.get('visual', '')}")
            st.write(f"**Texto en pantalla:** {scene.get('text_on_screen', '')}")
            st.write(f"**Acción primaria:** {visual_plan.get('primary_action', '')}")
            st.write(f"**Intención visual:** {visual_plan.get('visual_intent', scored_scene.get('visual_intent', ''))}")
            st.write(f"**Query:** `{scored_scene.get('query', visual_plan.get('search_query_en', ''))}`")

            suggestions = scored_scene.get("suggestions", [])
            options = build_scene_options(asset_type, suggestions)
            previous_choice = previous_choices.get(scene_number, "")
            default_index = get_option_index(options, previous_choice)

            choice = st.radio(
                "Selecciona máximo un asset para esta escena",
                options=[option["value"] for option in options],
                format_func=lambda value, scene_options=options: get_option_label(scene_options, value),
                index=default_index,
                key=f"scene_{scene_number}_asset_choice",
            )

            if choice:
                choices_by_scene[scene_number] = choice

            if choice == LOCAL_ASSET_CHOICE:
                local_uploads_by_scene[scene_number] = render_local_asset_uploader(
                    scene_number=scene_number,
                    previous_local_asset=previous_local_assets.get(scene_number, {}),
                    st=st,
                )

            render_scene_details(asset_type, visual_plan, suggestions, st)

    return choices_by_scene, local_uploads_by_scene


def build_scene_options(asset_type: str, suggestions: list[dict[str, Any]]) -> list[dict[str, str]]:
    options = [{"value": "", "label": "Ninguno por ahora"}]

    if asset_type in {"self_recorded", "screen_recording"} or not suggestions:
        options.append({"value": "manual_task", "label": "Tarea manual / pendiente"})

    options.append({"value": LOCAL_ASSET_CHOICE, "label": "Asset local / video propio"})

    for index, suggestion in enumerate(suggestions, start=1):
        provider_id = str(suggestion.get("provider_id", ""))
        score = suggestion.get("score", 0)
        duration = suggestion.get("duration", "")
        author = suggestion.get("author_name", "")
        options.append(
            {
                "value": provider_id,
                "label": f"Clip Pexels {index} · score {score} · {duration}s · {author}",
            }
        )

    return options


def get_option_index(options: list[dict[str, str]], value: str) -> int:
    for index, option in enumerate(options):
        if option["value"] == value:
            return index

    return 0


def get_option_label(options: list[dict[str, str]], value: str) -> str:
    for option in options:
        if option["value"] == value:
            return option["label"]

    return value


def render_local_asset_uploader(
    *,
    scene_number: int,
    previous_local_asset: dict[str, Any],
    st,
) -> Any:
    if previous_local_asset:
        st.success(
            "Asset local actual: "
            f"`{previous_local_asset.get('local_path', '')}`"
        )

    return st.file_uploader(
        "Sube o reemplaza el video local para esta escena",
        type=get_supported_upload_types(),
        key=f"scene_{scene_number}_local_asset",
    )


def prepare_local_assets_for_selection(
    *,
    choices_by_scene: dict[int, str],
    local_uploads_by_scene: dict[int, Any],
    previous_local_assets: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    local_assets = {}

    for scene_number, choice in choices_by_scene.items():
        if choice != LOCAL_ASSET_CHOICE:
            continue

        uploaded_file = local_uploads_by_scene.get(scene_number)

        if uploaded_file is not None:
            local_assets[scene_number] = save_uploaded_local_asset(
                local_assets_dir=LOCAL_ASSETS_DIR,
                scene_number=scene_number,
                original_filename=uploaded_file.name,
                content=uploaded_file.getvalue(),
            )
            continue

        if scene_number in previous_local_assets:
            local_assets[scene_number] = previous_local_assets[scene_number]
            continue

        local_assets[scene_number] = {}

    return local_assets


def get_supported_upload_types() -> list[str]:
    return sorted(extension.removeprefix(".") for extension in SUPPORTED_VIDEO_EXTENSIONS)


def render_scene_details(
    asset_type: str,
    visual_plan: dict[str, Any],
    suggestions: list[dict[str, Any]],
    st,
) -> None:
    if asset_type == "self_recorded":
        st.warning("Tarea manual: grabarte tú.")

    if asset_type == "screen_recording":
        st.warning("Tarea manual: grabar pantalla.")

    if not suggestions:
        st.info("Esta escena no tiene clips de Pexels.")
        return

    for suggestion in suggestions:
        render_suggestion(suggestion, st)


def render_suggestion(suggestion: dict[str, Any], st) -> None:
    columns = st.columns([1, 2])

    with columns[0]:
        thumbnail_url = suggestion.get("thumbnail_url")

        if thumbnail_url:
            st.image(thumbnail_url, width="stretch")
        else:
            st.caption("Sin thumbnail")

    with columns[1]:
        st.subheader(f"Score {suggestion.get('score', 0)}")
        st.write(f"**Orientación:** {suggestion.get('orientation', '')}")
        st.write(f"**Duración:** {suggestion.get('duration', '')}s")
        st.write(
            f"**Resolución:** {suggestion.get('width', '')} × {suggestion.get('height', '')}"
        )
        st.write(f"**Autor:** {suggestion.get('author_name', '')}")
        st.write(f"[Abrir preview]({suggestion.get('preview_url', '')})")
        st.write(f"[Ver en Pexels]({suggestion.get('page_url', '')})")

        with st.expander("Score breakdown"):
            st.json(suggestion.get("score_breakdown", {}))


def index_by_scene(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed = {}

    for item in items:
        try:
            scene_number = int(item.get("scene"))
        except (TypeError, ValueError):
            continue

        indexed[scene_number] = item

    return indexed


def load_previous_selection(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"project_title": "", "selected_assets": []}

    return load_json(path)
