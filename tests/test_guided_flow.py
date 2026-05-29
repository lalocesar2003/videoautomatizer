import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from panel.guided_flow import (
    LOCAL_ASSET_CHOICE,
    PREVIEW_WAIT_MESSAGE,
    build_selection_signature,
    build_clip_links,
    build_scene_options,
    build_scene_tab_labels,
    build_script_draft,
    default_script_template,
    get_missing_paths,
    get_option_index,
    get_option_label,
    is_preview_enabled,
    mark_selection_confirmed,
    prepare_local_assets_for_selection,
    run_preview_pipeline_with_progress,
    run_phase_sequence,
    sync_selection_confirmation,
)
from panel.pipeline_control import PhaseRunResult


class FakeUpload:
    name = "demo video.mp4"

    def getvalue(self) -> bytes:
        return b"video"


class FakeProgress:
    def __init__(self) -> None:
        self.values = []

    def progress(self, value: float) -> None:
        self.values.append(value)


class FakeStatus:
    def __init__(self) -> None:
        self.messages = []

    def write(self, value: str) -> None:
        self.messages.append(value)


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state = {}
        self.infos = []
        self.successes = []
        self.errors = []
        self.progress_bar = FakeProgress()
        self.status = FakeStatus()

    def info(self, value: str) -> None:
        self.infos.append(value)

    def success(self, value: str) -> None:
        self.successes.append(value)

    def error(self, value: str) -> None:
        self.errors.append(value)

    def progress(self, value: float) -> FakeProgress:
        self.progress_bar.progress(value)
        return self.progress_bar

    def empty(self) -> FakeStatus:
        return self.status


class GuidedFlowTests(unittest.TestCase):
    def test_build_script_draft_keeps_existing_script_first(self) -> None:
        existing = 'Guion para TikTok: "Existente"'

        self.assertEqual(
            build_script_draft(prompt="nuevo brief", current_script=existing),
            existing,
        )

    def test_build_script_draft_uses_prompt_when_no_script_exists(self) -> None:
        result = build_script_draft(
            prompt="Video para vender un sistema de cobranza",
            current_script="",
        )

        self.assertIn('Guion para TikTok: "Video promocional"', result)
        self.assertIn("Video para vender un sistema de cobranza", result)
        self.assertIn("• Visual:", result)
        self.assertIn("• Texto en pantalla:", result)
        self.assertIn("• Audio:", result)

    def test_build_script_draft_returns_template_without_prompt(self) -> None:
        self.assertEqual(
            build_script_draft(prompt="", current_script=""),
            default_script_template(),
        )

    def test_get_missing_paths_returns_only_missing_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing_path = root / "data" / "scenes.json"
            missing_path = root / "data" / "visual_plan.json"
            existing_path.parent.mkdir(parents=True)
            existing_path.write_text("{}", encoding="utf-8")

            self.assertEqual(get_missing_paths([existing_path, missing_path]), [missing_path])

    def test_build_scene_tab_labels_uses_scene_numbers(self) -> None:
        labels = build_scene_tab_labels([
            {"scene": 3},
            {"scene": 7},
            {"scene": "bad"},
        ])

        self.assertEqual(labels, ["Escena 3", "Escena 7", "Escena 3"])

    def test_build_scene_options_adds_manual_for_manual_or_empty_scenes(self) -> None:
        manual_options = build_scene_options("screen_recording", [])
        stock_options = build_scene_options(
            "stock",
            [
                {
                    "provider_id": "clip-1",
                    "score": 95,
                    "duration": 10,
                    "author_name": "Autor",
                }
            ],
        )

        self.assertIn("manual_task", [option["value"] for option in manual_options])
        self.assertIn(LOCAL_ASSET_CHOICE, [option["value"] for option in manual_options])
        self.assertNotIn("manual_task", [option["value"] for option in stock_options])
        self.assertIn("clip-1", [option["value"] for option in stock_options])

    def test_get_option_helpers_find_existing_value(self) -> None:
        options = [
            {"value": "", "label": "Ninguno"},
            {"value": "clip-1", "label": "Clip 1"},
        ]

        self.assertEqual(get_option_index(options, "clip-1"), 1)
        self.assertEqual(get_option_index(options, "missing"), 0)
        self.assertEqual(get_option_label(options, "clip-1"), "Clip 1")
        self.assertEqual(get_option_label(options, "missing"), "missing")

    def test_prepare_local_assets_preserves_previous_local_asset(self) -> None:
        result = prepare_local_assets_for_selection(
            choices_by_scene={3: LOCAL_ASSET_CHOICE},
            local_uploads_by_scene={3: None},
            previous_local_assets={3: {"local_path": "local_assets/scene_03.mp4"}},
        )

        self.assertEqual(result[3]["local_path"], "local_assets/scene_03.mp4")

    def test_prepare_local_assets_saves_uploaded_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch("panel.guided_flow.LOCAL_ASSETS_DIR", Path(temp_dir) / "local_assets"):
                result = prepare_local_assets_for_selection(
                    choices_by_scene={2: LOCAL_ASSET_CHOICE},
                    local_uploads_by_scene={2: FakeUpload()},
                    previous_local_assets={},
                )

            local_path = Path(result[2]["local_path"])
            self.assertTrue(local_path.exists())
            self.assertTrue(local_path.name.startswith("scene_02_demo_video"))
            self.assertEqual(local_path.read_bytes(), b"video")

    def test_build_selection_signature_tracks_choices_and_local_assets(self) -> None:
        signature = build_selection_signature(
            choices_by_scene={
                2: LOCAL_ASSET_CHOICE,
                1: "clip-1",
            },
            local_uploads_by_scene={2: None},
            previous_local_assets={2: {"local_path": "local_assets/scene_02.mp4"}},
        )

        self.assertEqual(
            signature,
            (
                (1, "clip-1", ""),
                (2, LOCAL_ASSET_CHOICE, "local_assets/scene_02.mp4"),
            ),
        )

    def test_build_selection_signature_tracks_uploaded_filename(self) -> None:
        signature = build_selection_signature(
            choices_by_scene={2: LOCAL_ASSET_CHOICE},
            local_uploads_by_scene={2: FakeUpload()},
            previous_local_assets={},
        )

        self.assertEqual(signature, ((2, LOCAL_ASSET_CHOICE, "demo video.mp4"),))

    def test_preview_requires_existing_and_confirmed_selection(self) -> None:
        with TemporaryDirectory() as temp_dir:
            selected_assets_path = Path(temp_dir) / "data" / "selected_assets.json"

            self.assertFalse(
                is_preview_enabled(
                    selected_assets_path=selected_assets_path,
                    selection_confirmed=True,
                )
            )

            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text("{}", encoding="utf-8")

            self.assertFalse(
                is_preview_enabled(
                    selected_assets_path=selected_assets_path,
                    selection_confirmed=False,
                )
            )
            self.assertTrue(
                is_preview_enabled(
                    selected_assets_path=selected_assets_path,
                    selection_confirmed=True,
                )
            )

    def test_sync_selection_confirmation_resets_when_selection_changes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            st = FakeStreamlit()
            selected_assets_path = Path(temp_dir) / "selected_assets.json"
            selected_assets_path.write_text("{}", encoding="utf-8")
            original_signature = ((1, "clip-1", ""),)
            changed_signature = ((1, "clip-2", ""),)

            mark_selection_confirmed(st, original_signature)

            self.assertTrue(
                sync_selection_confirmation(
                    st=st,
                    selection_signature=original_signature,
                    selected_assets_path=selected_assets_path,
                )
            )
            self.assertFalse(
                sync_selection_confirmation(
                    st=st,
                    selection_signature=changed_signature,
                    selected_assets_path=selected_assets_path,
                )
            )
            self.assertFalse(st.session_state["guided_selection_confirmed"])

    def test_run_phase_sequence_stops_on_first_failure(self) -> None:
        calls = []

        def fake_run_phase(phase_key: str):
            calls.append(phase_key)
            if phase_key == "resolve":
                return PhaseRunResult(
                    key=phase_key,
                    label="Resolver",
                    success=False,
                    message="falló",
                    output_path=Path("data/resolved_assets.json"),
                )
            return PhaseRunResult(
                key=phase_key,
                label=phase_key,
                success=True,
                message="ok",
                output_path=Path("out.json"),
            )

        with patch("panel.guided_flow.run_phase", side_effect=fake_run_phase):
            results = run_phase_sequence(["export", "resolve", "timeline"])

        self.assertEqual(calls, ["export", "resolve"])
        self.assertEqual(len(results), 2)
        self.assertFalse(results[-1].success)

    def test_run_preview_pipeline_with_progress_reports_steps(self) -> None:
        calls = []

        def fake_run_phase(phase_key: str):
            calls.append(phase_key)
            return PhaseRunResult(
                key=phase_key,
                label=phase_key,
                success=True,
                message="ok",
                output_path=Path("out.json"),
            )

        st = FakeStreamlit()

        with patch("panel.guided_flow.run_phase", side_effect=fake_run_phase):
            results = run_preview_pipeline_with_progress(st)

        self.assertEqual(
            calls,
            ["export", "resolve", "timeline", "missing", "placeholders", "prepare", "render"],
        )
        self.assertEqual(len(results), 7)
        self.assertIn(PREVIEW_WAIT_MESSAGE, st.infos)
        self.assertEqual(st.progress_bar.values[-1], 1.0)
        self.assertIn("1/7 Exportando assets…", st.status.messages)
        self.assertIn("Preview generado.", st.status.messages)

    def test_run_preview_pipeline_with_progress_stops_on_failure(self) -> None:
        calls = []

        def fake_run_phase(phase_key: str):
            calls.append(phase_key)
            return PhaseRunResult(
                key=phase_key,
                label=phase_key,
                success=phase_key != "timeline",
                message="falló timeline" if phase_key == "timeline" else "ok",
                output_path=Path("out.json"),
            )

        st = FakeStreamlit()

        with patch("panel.guided_flow.run_phase", side_effect=fake_run_phase):
            results = run_preview_pipeline_with_progress(st)

        self.assertEqual(calls, ["export", "resolve", "timeline"])
        self.assertEqual(len(results), 3)
        self.assertTrue(any("falló timeline" in error for error in st.errors))

    def test_build_clip_links_returns_preview_and_page_links(self) -> None:
        links = build_clip_links(
            {
                "preview_url": "https://videos.example/clip.mp4",
                "page_url": "https://pexels.example/clip",
            }
        )

        self.assertEqual(len(links), 2)
        self.assertIn("Preview", links[0])
        self.assertIn("Pexels", links[1])


if __name__ == "__main__":
    unittest.main()
