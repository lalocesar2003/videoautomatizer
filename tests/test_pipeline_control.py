import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from panel.pipeline_control import (
    PHASES,
    PREVIEW_VIDEO_PATH,
    get_phase_by_key,
    get_phase_status,
    get_pipeline_statuses,
    get_runnable_phases,
    render_preview,
    run_phase,
)


class FakeStreamlit:
    def __init__(self) -> None:
        self.calls = []

    def subheader(self, value: str) -> None:
        self.calls.append(("subheader", value))

    def info(self, value: str) -> None:
        self.calls.append(("info", value))

    def success(self, value: str) -> None:
        self.calls.append(("success", value))

    def video(self, value: str) -> None:
        self.calls.append(("video", value))


class PipelineControlTests(unittest.TestCase):
    def test_phase_definitions_include_expected_outputs(self) -> None:
        phase_by_key = {phase.key: phase for phase in PHASES}

        self.assertEqual(phase_by_key["parse"].output_path, Path("data/scenes.json"))
        self.assertEqual(
            phase_by_key["selection"].output_path,
            Path("data/selected_assets.json"),
        )
        self.assertEqual(
            phase_by_key["render"].output_path,
            Path("exports/preview_video.mp4"),
        )

    def test_get_phase_status_detects_ready_and_pending_outputs(self) -> None:
        phase = get_phase_by_key("parse")

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pending_status = get_phase_status(phase, root)

            self.assertFalse(pending_status.exists)
            self.assertEqual(pending_status.status_icon, "⚠️")
            self.assertEqual(pending_status.status_label, "Pendiente")

            output_path = root / phase.output_path
            output_path.parent.mkdir(parents=True)
            output_path.write_text("{}", encoding="utf-8")

            ready_status = get_phase_status(phase, root)

            self.assertTrue(ready_status.exists)
            self.assertEqual(ready_status.status_icon, "✅")
            self.assertEqual(ready_status.status_label, "Listo")

    def test_get_pipeline_statuses_returns_one_status_per_phase(self) -> None:
        statuses = get_pipeline_statuses()

        self.assertEqual(len(statuses), len(PHASES))
        self.assertEqual([status.key for status in statuses], [phase.key for phase in PHASES])

    def test_get_runnable_phases_excludes_manual_selection(self) -> None:
        runnable_keys = [phase.key for phase in get_runnable_phases()]

        self.assertIn("parse", runnable_keys)
        self.assertIn("render", runnable_keys)
        self.assertNotIn("selection", runnable_keys)

    def test_run_phase_executes_only_selected_runner(self) -> None:
        calls = []

        result = run_phase(
            "parse",
            runners={
                "parse": lambda: calls.append("parse") or {"ok": True},
                "score": lambda: calls.append("score"),
            },
        )

        self.assertTrue(result.success)
        self.assertEqual(calls, ["parse"])
        self.assertEqual(result.data, {"ok": True})
        self.assertIn("Parsear guion terminado", result.message)

    def test_run_phase_reports_runner_errors_without_raising(self) -> None:
        def failing_runner() -> None:
            raise RuntimeError("Falta PEXELS_API_KEY")

        result = run_phase("search", runners={"search": failing_runner})

        self.assertFalse(result.success)
        self.assertIn("Buscar en Pexels falló", result.message)
        self.assertIn("Falta PEXELS_API_KEY", result.message)

    def test_run_phase_rejects_manual_selection(self) -> None:
        result = run_phase("selection", runners={})

        self.assertFalse(result.success)
        self.assertIn("no tiene botón", result.message)

    def test_unknown_phase_fails_clearly(self) -> None:
        with self.assertRaises(ValueError):
            get_phase_by_key("does-not-exist")

    def test_render_preview_shows_info_when_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            st = FakeStreamlit()
            render_preview(st, root_dir=Path(temp_dir))

        self.assertIn(("subheader", "Preview final"), st.calls)
        self.assertTrue(any(call[0] == "info" for call in st.calls))
        self.assertFalse(any(call[0] == "video" for call in st.calls))

    def test_render_preview_embeds_video_when_available(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview_path = root / PREVIEW_VIDEO_PATH
            preview_path.parent.mkdir(parents=True)
            preview_path.write_bytes(b"video")

            st = FakeStreamlit()
            render_preview(st, root_dir=root)

        self.assertTrue(any(call[0] == "success" for call in st.calls))
        self.assertIn(("video", str(preview_path)), st.calls)


if __name__ == "__main__":
    unittest.main()
