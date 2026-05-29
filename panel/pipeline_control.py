from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


Runner = Callable[[], Any]


@dataclass(frozen=True)
class PipelinePhase:
    key: str
    label: str
    output_path: Path
    runner_name: str | None = None
    help_text: str = ""


@dataclass(frozen=True)
class PhaseStatus:
    key: str
    label: str
    output_path: Path
    exists: bool
    status_label: str
    status_icon: str
    can_run: bool


@dataclass(frozen=True)
class PhaseRunResult:
    key: str
    label: str
    success: bool
    message: str
    output_path: Path
    data: Any = None


PHASES = [
    PipelinePhase(
        key="parse",
        label="Parsear guion",
        output_path=Path("data/scenes.json"),
        runner_name="run_parse",
        help_text="script.md → data/scenes.json",
    ),
    PipelinePhase(
        key="classify",
        label="Clasificar escenas",
        output_path=Path("data/visual_plan.json"),
        runner_name="run_classify",
        help_text="data/scenes.json → data/visual_plan.json",
    ),
    PipelinePhase(
        key="search",
        label="Buscar en Pexels",
        output_path=Path("data/pexels_results.json"),
        runner_name="run_search",
        help_text="data/visual_plan.json → data/pexels_results.json",
    ),
    PipelinePhase(
        key="score",
        label="Puntuar clips",
        output_path=Path("data/scored_results.json"),
        runner_name="run_score",
        help_text="data/pexels_results.json → data/scored_results.json",
    ),
    PipelinePhase(
        key="selection",
        label="Selección manual",
        output_path=Path("data/selected_assets.json"),
        runner_name=None,
        help_text="Se genera con el formulario de selección del panel.",
    ),
    PipelinePhase(
        key="export",
        label="Exportar seleccionados",
        output_path=Path("exports/selected_broll.zip"),
        runner_name="run_export",
        help_text="data/selected_assets.json → exports/clips/ + ZIP",
    ),
    PipelinePhase(
        key="resolve",
        label="Resolver assets",
        output_path=Path("data/resolved_assets.json"),
        runner_name="run_resolve",
        help_text="selected_assets + escenas → resolved_assets",
    ),
    PipelinePhase(
        key="timeline",
        label="Generar timeline",
        output_path=Path("data/timeline.json"),
        runner_name="run_timeline",
        help_text="resolved_assets → timeline ordenado",
    ),
    PipelinePhase(
        key="missing",
        label="Detectar faltantes",
        output_path=Path("data/missing_scenes.json"),
        runner_name="run_missing",
        help_text="timeline → reporte de escenas no listas",
    ),
    PipelinePhase(
        key="placeholders",
        label="Generar placeholders",
        output_path=Path("exports/placeholders/placeholder_manifest.json"),
        runner_name="run_placeholders",
        help_text="missing_scenes + timeline → clips placeholder",
    ),
    PipelinePhase(
        key="prepare",
        label="Preparar clips",
        output_path=Path("exports/prepared_clips/prepared_manifest.json"),
        runner_name="run_prepare",
        help_text="clips/placeholders → prepared_clips",
    ),
    PipelinePhase(
        key="render",
        label="Renderizar preview",
        output_path=Path("exports/preview_video.mp4"),
        runner_name="run_render",
        help_text="prepared_clips/placeholders → preview_video.mp4",
    ),
]


PHASES_BY_KEY = {phase.key: phase for phase in PHASES}
PREVIEW_VIDEO_PATH = Path("exports/preview_video.mp4")


def get_phase_status(phase: PipelinePhase, root_dir: Path = Path(".")) -> PhaseStatus:
    output_path = root_dir / phase.output_path
    exists = output_path.exists()

    return PhaseStatus(
        key=phase.key,
        label=phase.label,
        output_path=phase.output_path,
        exists=exists,
        status_label="Listo" if exists else "Pendiente",
        status_icon="✅" if exists else "⚠️",
        can_run=phase.runner_name is not None,
    )


def get_pipeline_statuses(
    phases: list[PipelinePhase] | None = None,
    root_dir: Path = Path("."),
) -> list[PhaseStatus]:
    selected_phases = phases or PHASES
    return [get_phase_status(phase, root_dir) for phase in selected_phases]


def get_runnable_phases(phases: list[PipelinePhase] | None = None) -> list[PipelinePhase]:
    selected_phases = phases or PHASES
    return [phase for phase in selected_phases if phase.runner_name]


def run_phase(
    phase_key: str,
    *,
    runners: dict[str, Runner] | None = None,
) -> PhaseRunResult:
    phase = get_phase_by_key(phase_key)

    if not phase.runner_name:
        return PhaseRunResult(
            key=phase.key,
            label=phase.label,
            success=False,
            message="Esta fase no tiene botón de ejecución automática.",
            output_path=phase.output_path,
        )

    runner = get_runner(phase, runners)

    try:
        data = runner()
    except Exception as error:  # noqa: BLE001 - Streamlit debe mostrar el error real al usuario.
        return PhaseRunResult(
            key=phase.key,
            label=phase.label,
            success=False,
            message=f"{phase.label} falló: {error}",
            output_path=phase.output_path,
        )

    return PhaseRunResult(
        key=phase.key,
        label=phase.label,
        success=True,
        message=f"{phase.label} terminado. Output esperado: {phase.output_path}",
        output_path=phase.output_path,
        data=data,
    )


def get_phase_by_key(phase_key: str) -> PipelinePhase:
    phase = PHASES_BY_KEY.get(phase_key)

    if not phase:
        valid_keys = ", ".join(PHASES_BY_KEY)
        raise ValueError(f"Fase desconocida: {phase_key}. Fases válidas: {valid_keys}")

    return phase


def get_runner(
    phase: PipelinePhase,
    runners: dict[str, Runner] | None,
) -> Runner:
    if runners and phase.key in runners:
        return runners[phase.key]

    runner_map = build_main_runner_map()
    runner = runner_map.get(phase.key)

    if runner is None:
        raise ValueError(f"No hay runner configurado para la fase {phase.key}")

    return runner


def build_main_runner_map() -> dict[str, Runner]:
    import main

    return {
        "parse": main.run_parse,
        "classify": main.run_classify,
        "search": main.run_search,
        "score": main.run_score,
        "export": main.run_export,
        "resolve": main.run_resolve,
        "timeline": main.run_timeline,
        "missing": main.run_missing,
        "placeholders": main.run_placeholders,
        "prepare": main.run_prepare,
        "render": main.run_render,
    }


def render_pipeline_control(
    st,
    *,
    root_dir: Path = Path("."),
    runners: dict[str, Runner] | None = None,
) -> None:
    st.header("🕹️ Control del pipeline")
    st.caption(
        "Ejecuta una fase a la vez. El botón único de flujo completo queda para el siguiente issue."
    )

    render_status_summary(st, root_dir=root_dir)
    render_phase_buttons(st, root_dir=root_dir, runners=runners)
    render_preview(st, root_dir=root_dir)


def render_status_summary(st, *, root_dir: Path) -> None:
    statuses = get_pipeline_statuses(root_dir=root_dir)
    ready_count = sum(1 for status in statuses if status.exists)

    st.write(f"**Estado general:** {ready_count}/{len(statuses)} outputs listos")

    rows = [
        {
            "Fase": status.label,
            "Estado": f"{status.status_icon} {status.status_label}",
            "Output": str(status.output_path),
        }
        for status in statuses
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def render_phase_buttons(
    st,
    *,
    root_dir: Path,
    runners: dict[str, Runner] | None,
) -> None:
    st.subheader("Ejecutar fase individual")

    for phase in get_runnable_phases():
        status = get_phase_status(phase, root_dir)
        columns = st.columns([2, 3, 2])

        with columns[0]:
            st.write(f"**{phase.label}**")
            st.caption(phase.help_text)

        with columns[1]:
            st.write(f"{status.status_icon} {status.status_label}")
            st.code(str(phase.output_path), language="text")

        with columns[2]:
            if st.button(f"Ejecutar", key=f"run_{phase.key}"):
                with st.spinner(f"Ejecutando {phase.label}…"):
                    result = run_phase(phase.key, runners=runners)

                if result.success:
                    st.success(result.message)
                else:
                    st.error(result.message)


def render_preview(st, *, root_dir: Path) -> None:
    preview_path = root_dir / PREVIEW_VIDEO_PATH

    st.subheader("Preview final")

    if not preview_path.exists():
        st.info("Todavía no existe exports/preview_video.mp4.")
        return

    st.success(f"Preview disponible: `{PREVIEW_VIDEO_PATH}`")
    st.video(str(preview_path))
