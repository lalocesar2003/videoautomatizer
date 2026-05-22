from pathlib import Path
from typing import Any

from selection.asset_selector import (
    build_selected_assets,
    count_suggestions,
    get_selected_provider_ids,
    load_json,
    save_selected_assets,
)


SCORED_RESULTS_PATH = Path("data/scored_results.json")
SELECTED_ASSETS_PATH = Path("data/selected_assets.json")


def run_streamlit_panel(
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

    scored_results = load_json(scored_results_path)
    previous_selection = load_previous_selection(selected_assets_path)
    previous_provider_ids = get_selected_provider_ids(previous_selection)

    st.write(f"**Proyecto:** {scored_results.get('project_title', 'Proyecto sin título')}")
    st.write(f"**Escenas:** {len(scored_results.get('results', []))}")
    st.write(f"**Sugerencias:** {count_suggestions(scored_results)}")

    selected_provider_ids = render_scenes(scored_results, previous_provider_ids, st)

    if st.button("Guardar selección", type="primary"):
        selected_assets = build_selected_assets(scored_results, selected_provider_ids)
        save_selected_assets(selected_assets_path, selected_assets)
        st.success(
            f"Selección guardada en {selected_assets_path} "
            f"({len(selected_assets['selected_assets'])} clips)."
        )
        st.json(selected_assets)

    st.info("Fase 5A: no se descargan clips y no se genera ZIP todavía.")


def render_scenes(
    scored_results: dict[str, Any],
    previous_provider_ids: set[str],
    st,
) -> set[str]:
    selected_provider_ids = set()

    for scene in scored_results.get("results", []):
        scene_title = f"Escena {scene.get('scene')} · {scene.get('asset_type')}"

        with st.expander(scene_title, expanded=True):
            st.write(f"**Intención visual:** {scene.get('visual_intent', '')}")
            st.write(f"**Query:** `{scene.get('query', '')}`")

            suggestions = scene.get("suggestions", [])

            if not suggestions:
                st.warning("Esta escena no tiene sugerencias.")
                continue

            for suggestion in suggestions:
                provider_id = str(suggestion.get("provider_id", ""))

                if render_suggestion(scene, suggestion, provider_id, previous_provider_ids, st):
                    selected_provider_ids.add(provider_id)

    return selected_provider_ids


def render_suggestion(
    scene: dict[str, Any],
    suggestion: dict[str, Any],
    provider_id: str,
    previous_provider_ids: set[str],
    st,
) -> bool:
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

        return st.checkbox(
            "Seleccionar clip",
            value=provider_id in previous_provider_ids,
            key=build_checkbox_key(scene, suggestion),
        )


def build_checkbox_key(scene: dict[str, Any], suggestion: dict[str, Any]) -> str:
    return f"scene_{scene.get('scene')}_clip_{suggestion.get('provider_id')}"


def load_previous_selection(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"project_title": "", "selected_assets": []}

    return load_json(path)
