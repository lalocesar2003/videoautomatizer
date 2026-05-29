from __future__ import annotations

from pathlib import Path
from typing import Any

from panel.pipeline_control import PhaseRunResult, render_pipeline_control, run_phase
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


SCRIPT_PATH = Path("script.md")
SCENES_PATH = Path("data/scenes.json")
VISUAL_PLAN_PATH = Path("data/visual_plan.json")
SCORED_RESULTS_PATH = Path("data/scored_results.json")
SELECTED_ASSETS_PATH = Path("data/selected_assets.json")
LOCAL_ASSETS_DIR = Path("local_assets")
PREVIEW_VIDEO_PATH = Path("exports/preview_video.mp4")
VIDEO_INPUT_PATHS = [SCENES_PATH, VISUAL_PLAN_PATH, SCORED_RESULTS_PATH]
SCENE_BOOTSTRAP_PHASES = ["parse", "classify", "search", "score"]
PREVIEW_PHASES = [
    "export",
    "resolve",
    "timeline",
    "missing",
    "placeholders",
    "prepare",
    "render",
]


def run_guided_streamlit_flow(
    *,
    script_path: Path = SCRIPT_PATH,
    scenes_path: Path = SCENES_PATH,
    visual_plan_path: Path = VISUAL_PLAN_PATH,
    scored_results_path: Path = SCORED_RESULTS_PATH,
    selected_assets_path: Path = SELECTED_ASSETS_PATH,
    preview_video_path: Path = PREVIEW_VIDEO_PATH,
) -> None:
    import streamlit as st

    st.set_page_config(
        page_title="Videoautomatizer",
        page_icon="🎬",
        layout="wide",
    )

    apply_guided_styles(st)
    st.title("🎬 Videoautomatizer")
    st.caption("Crea el guion, resuelve escenas y genera un preview visual.")

    render_script_section(st, script_path=script_path)
    render_video_section(
        st,
        scenes_path=scenes_path,
        visual_plan_path=visual_plan_path,
        scored_results_path=scored_results_path,
        selected_assets_path=selected_assets_path,
        preview_video_path=preview_video_path,
    )

    with st.expander("Modo avanzado / Debug", expanded=False):
        render_pipeline_control(st)


# ---------------------------------------------------------------------------
# Guion
# ---------------------------------------------------------------------------


def render_script_section(st, *, script_path: Path) -> None:
    with st.container(border=True):
        st.header("Describe tu guion")
        prompt = st.text_area(
            "Idea o brief del video",
            value=st.session_state.get("guided_prompt", ""),
            height=120,
            key="guided_prompt",
            placeholder="Ej: Hazme un video de 45 segundos para vender un sistema de cobranza...",
        )

        if st.button("Generar Guion", type="primary", use_container_width=True):
            st.session_state["guided_script_text"] = build_script_draft(
                prompt=prompt,
                current_script=read_text_or_empty(script_path),
            )
            st.success("Guion preparado para edición. Revísalo antes de aprobar.")

    with st.container(border=True):
        st.header("Edita tu guion")
        script_value = get_script_editor_value(st, script_path)
        edited_script = st.text_area(
            "Guion editable",
            value=script_value,
            height=260,
            key="guided_script_editor",
            label_visibility="collapsed",
        )

        approve_col, regenerate_col = st.columns(2)

        with approve_col:
            if st.button("Aprobar Guion", type="primary", use_container_width=True):
                save_text(script_path, edited_script)
                st.session_state["guided_script_text"] = edited_script
                st.success(f"Guion aprobado y guardado en {script_path}.")

        with regenerate_col:
            if st.button("Regenerar", use_container_width=True):
                st.session_state["guided_script_text"] = build_script_draft(
                    prompt=prompt,
                    current_script="",
                )
                st.rerun()


# ---------------------------------------------------------------------------
# Video guiado
# ---------------------------------------------------------------------------


def render_video_section(
    st,
    *,
    scenes_path: Path,
    visual_plan_path: Path,
    scored_results_path: Path,
    selected_assets_path: Path,
    preview_video_path: Path,
) -> None:
    st.markdown("---")

    with st.container(border=True):
        st.header("Crear video")
        st.caption("Revisa escena por escena. Elige un clip o sube tu propio video local.")

        missing_inputs = get_missing_paths([scenes_path, visual_plan_path, scored_results_path])

        if missing_inputs:
            render_missing_video_inputs(st, missing_inputs)
            return

        scenes_data = load_json(scenes_path)
        visual_plan_data = load_json(visual_plan_path)
        scored_results = load_json(scored_results_path)
        previous_selection = load_previous_selection(selected_assets_path)

        scenes = scenes_data.get("scenes", [])
        visual_plan_by_scene = index_by_scene(visual_plan_data.get("visual_plan", []))
        scored_results_by_scene = index_by_scene(scored_results.get("results", []))
        previous_choices = get_choices_by_scene(previous_selection)
        previous_local_assets = get_local_assets_by_scene(previous_selection)

        st.write(f"**Proyecto:** {get_project_title(scenes_data, scored_results)}")
        st.write(f"**Escenas:** {len(scenes)} · **Clips sugeridos:** {count_suggestions(scored_results)}")

        choices_by_scene, local_uploads_by_scene = render_scene_tabs(
            st,
            scenes=scenes,
            visual_plan_by_scene=visual_plan_by_scene,
            scored_results_by_scene=scored_results_by_scene,
            previous_choices=previous_choices,
            previous_local_assets=previous_local_assets,
        )

        render_video_actions(
            st,
            scenes=scenes,
            visual_plan_by_scene=visual_plan_by_scene,
            scored_results_by_scene=scored_results_by_scene,
            scored_results=scored_results,
            choices_by_scene=choices_by_scene,
            local_uploads_by_scene=local_uploads_by_scene,
            previous_local_assets=previous_local_assets,
            selected_assets_path=selected_assets_path,
            preview_video_path=preview_video_path,
        )


def render_missing_video_inputs(st, missing_inputs: list[Path]) -> None:
    st.warning(
        "Faltan archivos base para revisar escenas: "
        + ", ".join(f"`{path}`" for path in missing_inputs)
    )
    st.info("Aprueba el guion y prepara escenas/clips sugeridos antes de crear el video.")

    if st.button("Preparar escenas y clips sugeridos", type="primary", use_container_width=True):
        results = run_phase_sequence(SCENE_BOOTSTRAP_PHASES)
        render_phase_sequence_results(st, results)


def render_scene_tabs(
    st,
    *,
    scenes: list[dict[str, Any]],
    visual_plan_by_scene: dict[int, dict[str, Any]],
    scored_results_by_scene: dict[int, dict[str, Any]],
    previous_choices: dict[int, str],
    previous_local_assets: dict[int, dict[str, Any]],
) -> tuple[dict[int, str], dict[int, Any]]:
    choices_by_scene = {}
    local_uploads_by_scene = {}

    if not scenes:
        st.info("Todavía no hay escenas parseadas.")
        return choices_by_scene, local_uploads_by_scene

    tabs = st.tabs(build_scene_tab_labels(scenes))

    for scene, tab in zip(scenes, tabs):
        scene_number = int_or_zero(scene.get("scene"))
        visual_plan = visual_plan_by_scene.get(scene_number, {})
        scored_scene = scored_results_by_scene.get(scene_number, {})
        suggestions = scored_scene.get("suggestions", [])
        previous_choice = previous_choices.get(scene_number, "")

        with tab:
            render_scene_context(st, scene=scene, visual_plan=visual_plan)
            render_manual_requirement(st, scene=scene, visual_plan=visual_plan, suggestions=suggestions)

            choice = render_scene_asset_choice(
                st,
                scene=scene,
                visual_plan=visual_plan,
                suggestions=suggestions,
                previous_choice=previous_choice,
            )

            uploaded_file = render_scene_local_upload(
                st,
                scene_number=scene_number,
                previous_local_asset=previous_local_assets.get(scene_number, {}),
            )

            if uploaded_file is not None:
                choice = LOCAL_ASSET_CHOICE
                local_uploads_by_scene[scene_number] = uploaded_file
            elif choice == LOCAL_ASSET_CHOICE:
                local_uploads_by_scene[scene_number] = None

            if choice:
                choices_by_scene[scene_number] = choice

            render_clip_cards(st, suggestions=suggestions, selected_choice=choice)

    return choices_by_scene, local_uploads_by_scene


def render_scene_context(
    st,
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
) -> None:
    st.markdown(
        f"""
        <div class="scene-meta">
          <p><span>Tiempo:</span><br>{clean_text(scene.get('start'))} - {clean_text(scene.get('end'))}</p>
          <p><span>Sección:</span><br>{clean_text(scene.get('section'))}</p>
          <p><span>Texto en pantalla:</span><br><strong>{clean_text(scene.get('text_on_screen'))}</strong></p>
          <p><span>Visual:</span><br>{clean_text(scene.get('visual'))}</p>
          <p><span>Tipo:</span><br>{clean_text(visual_plan.get('asset_type')) or 'sin clasificar'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    primary_action = clean_text(visual_plan.get("primary_action"))
    if primary_action:
        st.caption(f"Acción recomendada: {primary_action}")


def render_manual_requirement(
    st,
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    suggestions: list[dict[str, Any]],
) -> None:
    asset_type = clean_text(visual_plan.get("asset_type"))
    requires_manual = asset_type in {"self_recorded", "screen_recording"} or not suggestions

    if not requires_manual:
        return

    action = clean_text(visual_plan.get("primary_action")) or clean_text(scene.get("visual"))
    st.warning("Tarea manual requerida")
    st.write(action)


def render_scene_asset_choice(
    st,
    *,
    scene: dict[str, Any],
    visual_plan: dict[str, Any],
    suggestions: list[dict[str, Any]],
    previous_choice: str,
) -> str:
    scene_number = int_or_zero(scene.get("scene"))
    options = build_scene_options(visual_plan.get("asset_type", ""), suggestions)
    default_index = get_option_index(options, previous_choice)

    return st.radio(
        "Selecciona máximo un asset para esta escena",
        options=[option["value"] for option in options],
        format_func=lambda value, scene_options=options: get_option_label(scene_options, value),
        index=default_index,
        key=f"guided_scene_{scene_number}_asset_choice",
    )


def render_scene_local_upload(
    st,
    *,
    scene_number: int,
    previous_local_asset: dict[str, Any],
) -> Any:
    with st.expander("Subir o reemplazar video", expanded=bool(previous_local_asset)):
        if previous_local_asset:
            st.success(f"Asset local actual: `{previous_local_asset.get('local_path', '')}`")

        return st.file_uploader(
            "Sube un video local para esta escena",
            type=get_supported_upload_types(),
            key=f"guided_scene_{scene_number}_local_asset",
        )


def render_clip_cards(st, *, suggestions: list[dict[str, Any]], selected_choice: str) -> None:
    st.subheader(f"Clips disponibles ({len(suggestions)})")

    if not suggestions:
        st.info("No hay clips disponibles para esta escena.")
        return

    for suggestion in suggestions:
        provider_id = clean_text(suggestion.get("provider_id"))
        selected_badge = " · Seleccionado" if provider_id == selected_choice else ""
        columns = st.columns([1, 5, 1])

        with columns[0]:
            thumbnail_url = suggestion.get("thumbnail_url")
            if thumbnail_url:
                st.image(thumbnail_url, width=92)
            else:
                st.caption(f"{suggestion.get('duration', '')}s")

        with columns[1]:
            st.markdown(f"**{clean_text(suggestion.get('author_name')) or 'Autor desconocido'}{selected_badge}**")
            st.caption(
                f"Score: {suggestion.get('score', 0)} · "
                f"Duración: {suggestion.get('duration', '')}s · "
                f"{suggestion.get('width', '')}×{suggestion.get('height', '')}"
            )
            links = build_clip_links(suggestion)
            if links:
                st.markdown(" · ".join(links), unsafe_allow_html=True)

        with columns[2]:
            if provider_id == selected_choice:
                st.success("Elegido")
            else:
                st.caption("Opción")


def render_video_actions(
    st,
    *,
    scenes: list[dict[str, Any]],
    visual_plan_by_scene: dict[int, dict[str, Any]],
    scored_results_by_scene: dict[int, dict[str, Any]],
    scored_results: dict[str, Any],
    choices_by_scene: dict[int, str],
    local_uploads_by_scene: dict[int, Any],
    previous_local_assets: dict[int, dict[str, Any]],
    selected_assets_path: Path,
    preview_video_path: Path,
) -> None:
    st.markdown("---")
    confirm_col, preview_col, generate_col = st.columns([1.2, 1, 1.2])

    with confirm_col:
        if st.button("Confirmar selección", use_container_width=True):
            save_selection_from_ui(
                st,
                scenes=scenes,
                visual_plan_by_scene=visual_plan_by_scene,
                scored_results_by_scene=scored_results_by_scene,
                scored_results=scored_results,
                choices_by_scene=choices_by_scene,
                local_uploads_by_scene=local_uploads_by_scene,
                previous_local_assets=previous_local_assets,
                selected_assets_path=selected_assets_path,
            )

    with preview_col:
        if st.button("Preview", use_container_width=True):
            if save_selection_from_ui(
                st,
                scenes=scenes,
                visual_plan_by_scene=visual_plan_by_scene,
                scored_results_by_scene=scored_results_by_scene,
                scored_results=scored_results,
                choices_by_scene=choices_by_scene,
                local_uploads_by_scene=local_uploads_by_scene,
                previous_local_assets=previous_local_assets,
                selected_assets_path=selected_assets_path,
            ):
                results = run_phase_sequence(PREVIEW_PHASES)
                render_phase_sequence_results(st, results)

    with generate_col:
        if st.button("Generar Video preliminar", type="primary", use_container_width=True):
            if save_selection_from_ui(
                st,
                scenes=scenes,
                visual_plan_by_scene=visual_plan_by_scene,
                scored_results_by_scene=scored_results_by_scene,
                scored_results=scored_results,
                choices_by_scene=choices_by_scene,
                local_uploads_by_scene=local_uploads_by_scene,
                previous_local_assets=previous_local_assets,
                selected_assets_path=selected_assets_path,
            ):
                results = run_phase_sequence(PREVIEW_PHASES)
                render_phase_sequence_results(st, results)

    if preview_video_path.exists():
        st.success(f"Preview disponible: `{preview_video_path}`")
        st.video(str(preview_video_path))
    else:
        st.info("Todavía no existe preview generado.")


def save_selection_from_ui(
    st,
    *,
    scenes: list[dict[str, Any]],
    visual_plan_by_scene: dict[int, dict[str, Any]],
    scored_results_by_scene: dict[int, dict[str, Any]],
    scored_results: dict[str, Any],
    choices_by_scene: dict[int, str],
    local_uploads_by_scene: dict[int, Any],
    previous_local_assets: dict[int, dict[str, Any]],
    selected_assets_path: Path,
) -> bool:
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
        return False

    save_selected_assets(selected_assets_path, selected_assets)
    st.success(
        f"Selección guardada en {selected_assets_path} "
        f"({len(selected_assets['selected_assets'])} assets)."
    )
    return True


# ---------------------------------------------------------------------------
# Helpers puros / testeables
# ---------------------------------------------------------------------------


def build_script_draft(*, prompt: str, current_script: str) -> str:
    cleaned_prompt = clean_text(prompt)
    cleaned_script = clean_text(current_script)

    if cleaned_script:
        return cleaned_script

    if not cleaned_prompt:
        return default_script_template()

    return (
        'Guion para TikTok: "Video promocional"\n\n'
        "[0:00 - 0:03] EL GANCHO\n"
        f"• Visual: {cleaned_prompt}\n"
        "• Texto en pantalla: Idea principal del video\n"
        "• Audio: Presenta el problema de forma directa.\n\n"
        "[0:03 - 0:12] DESARROLLO\n"
        "• Visual: Muestra el producto, servicio o proceso en acción.\n"
        "• Texto en pantalla: Beneficio principal\n"
        "• Audio: Explica por qué esto importa para el cliente.\n\n"
        "[0:12 - 0:20] CIERRE\n"
        "• Visual: Cierre con llamada a la acción.\n"
        "• Texto en pantalla: Escríbenos para más información\n"
        "• Audio: Invita a tomar acción.\n"
    )


def default_script_template() -> str:
    return (
        'Guion para TikTok: "Título del video"\n\n'
        "[0:00 - 0:03] EL GANCHO\n"
        "• Visual: ...\n"
        "• Texto en pantalla: ...\n"
        "• Audio: ...\n"
    )


def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def save_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def get_script_editor_value(st, script_path: Path) -> str:
    if "guided_script_text" in st.session_state:
        return st.session_state["guided_script_text"]

    return read_text_or_empty(script_path)


def get_missing_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if not path.exists()]


def build_scene_tab_labels(scenes: list[dict[str, Any]]) -> list[str]:
    labels = []

    for index, scene in enumerate(scenes, start=1):
        scene_number = int_or_zero(scene.get("scene")) or index
        labels.append(f"Escena {scene_number}")

    return labels


def build_scene_options(asset_type: str, suggestions: list[dict[str, Any]]) -> list[dict[str, str]]:
    options = [{"value": "", "label": "Ninguno por ahora"}]

    if clean_text(asset_type) in {"self_recorded", "screen_recording"} or not suggestions:
        options.append({"value": "manual_task", "label": "Tarea manual / pendiente"})

    options.append({"value": LOCAL_ASSET_CHOICE, "label": "Asset local / video propio"})

    for index, suggestion in enumerate(suggestions, start=1):
        provider_id = clean_text(suggestion.get("provider_id"))
        score = suggestion.get("score", 0)
        duration = suggestion.get("duration", "")
        author = clean_text(suggestion.get("author_name")) or "Autor desconocido"
        options.append(
            {
                "value": provider_id,
                "label": f"Clip {index} · score {score} · {duration}s · {author}",
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


def run_phase_sequence(phase_keys: list[str]) -> list[PhaseRunResult]:
    results = []

    for phase_key in phase_keys:
        result = run_phase(phase_key)
        results.append(result)

        if not result.success:
            break

    return results


def render_phase_sequence_results(st, results: list[PhaseRunResult]) -> None:
    for result in results:
        if result.success:
            st.success(result.message)
        else:
            st.error(result.message)
            return


def build_clip_links(suggestion: dict[str, Any]) -> list[str]:
    links = []
    preview_url = clean_text(suggestion.get("preview_url"))
    page_url = clean_text(suggestion.get("page_url"))

    if preview_url:
        links.append(f'<a href="{preview_url}" target="_blank">Preview</a>')

    if page_url:
        links.append(f'<a href="{page_url}" target="_blank">Pexels</a>')

    return links


def get_supported_upload_types() -> list[str]:
    return sorted(extension.removeprefix(".") for extension in SUPPORTED_VIDEO_EXTENSIONS)


def get_project_title(*sources: dict[str, Any]) -> str:
    for source in sources:
        title = clean_text(source.get("project_title"))
        if title:
            return title

    return "Proyecto sin título"


def load_previous_selection(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"project_title": "", "selected_assets": []}

    return load_json(path)


def index_by_scene(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed = {}

    for item in items:
        scene_number = int_or_zero(item.get("scene"))
        if scene_number:
            indexed[scene_number] = item

    return indexed


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def apply_guided_styles(st) -> None:
    st.markdown(
        """
        <style>
          .scene-meta {
            color: #d8dee9;
            line-height: 1.55;
          }
          .scene-meta span {
            color: #94a3b8;
            font-size: 0.95rem;
          }
          .stTabs [data-baseweb="tab-list"] {
            gap: 1.25rem;
          }
          .stTabs [data-baseweb="tab"] {
            font-size: 1.05rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
