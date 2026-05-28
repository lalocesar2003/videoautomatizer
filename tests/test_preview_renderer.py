import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rendering.preview_renderer import (
    build_ffmpeg_concat_command,
    build_ffmpeg_normalize_command,
    build_normalized_filename,
    render_preview_video,
)


class PreviewRendererTests(unittest.TestCase):
    def test_build_normalized_filename(self) -> None:
        self.assertEqual(build_normalized_filename(1), "scene_01_normalized.mp4")
        self.assertEqual(build_normalized_filename(12), "scene_12_normalized.mp4")

    def test_render_uses_prepared_clips_then_placeholder_fallback_in_order(self) -> None:
        commands = []

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared_dir = root / "exports" / "prepared_clips"
            placeholders_dir = root / "exports" / "placeholders"
            render_tmp_dir = root / "exports" / "render_tmp"
            output_path = root / "exports" / "preview_video.mp4"
            concat_list_path = root / "exports" / "concat_list.txt"
            manifest_path = root / "exports" / "preview_manifest.json"
            prepared_dir.mkdir(parents=True)
            placeholders_dir.mkdir(parents=True)

            (prepared_dir / "scene_01_ready.mp4").write_bytes(b"prepared-1")
            (prepared_dir / "scene_03_ready.mp4").write_bytes(b"prepared-3")
            (placeholders_dir / "scene_02_placeholder.mp4").write_bytes(b"placeholder-2")

            timeline_data = {
                "project_title": "Proyecto Test",
                "timeline": [
                    {"scene": 3, "duration_seconds": 12, "status": "ready"},
                    {"scene": 1, "duration_seconds": 3, "status": "ready"},
                    {"scene": 2, "duration_seconds": 5, "status": "needs_screen_recording"},
                ],
            }

            durations = {
                "scene_01_ready.mp4": 3.0,
                "scene_02_placeholder.mp4": 5.0,
                "scene_03_ready.mp4": 12.0,
            }

            def fake_duration_reader(path: Path) -> float:
                return durations[path.name]

            def fake_runner(command: list[str]) -> None:
                commands.append(command)

                if "concat" in command:
                    output_path.write_bytes(b"preview")
                    return

                Path(command[-1]).write_bytes(b"normalized")

            manifest = render_preview_video(
                timeline_data=timeline_data,
                prepared_clips_dir=prepared_dir,
                placeholders_dir=placeholders_dir,
                output_path=output_path,
                temp_dir=render_tmp_dir,
                concat_list_path=concat_list_path,
                manifest_path=manifest_path,
                ffmpeg_path="ffmpeg",
                duration_reader=fake_duration_reader,
                runner=fake_runner,
                generated_at="2026-05-27T00:00:00Z",
            )

            self.assertEqual(manifest["project_title"], "Proyecto Test")
            self.assertEqual(manifest["generated_at"], "2026-05-27T00:00:00Z")
            self.assertEqual(manifest["output_path"], str(output_path))
            self.assertEqual(manifest["summary"]["scene_count"], 3)
            self.assertEqual(manifest["summary"]["rendered_scene_count"], 3)
            self.assertEqual(manifest["summary"]["warning_count"], 1)
            self.assertEqual(manifest["summary"]["total_duration_seconds"], 20)
            self.assertEqual([item["scene"] for item in manifest["timeline"]], [1, 2, 3])
            self.assertEqual(manifest["timeline"][0]["strategy"], "prepared_clip")
            self.assertEqual(manifest["timeline"][1]["strategy"], "placeholder_fallback")
            self.assertEqual(manifest["timeline"][2]["strategy"], "prepared_clip")
            self.assertTrue(output_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(concat_list_path.exists())
            self.assertEqual(len(commands), 4)

            concat_lines = concat_list_path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(concat_lines[0].endswith("scene_01_normalized.mp4'"))
            self.assertTrue(concat_lines[1].endswith("scene_02_normalized.mp4'"))
            self.assertTrue(concat_lines[2].endswith("scene_03_normalized.mp4'"))

            saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest, manifest)

    def test_missing_prepared_and_placeholder_fails_clearly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaises(RuntimeError) as context:
                render_preview_video(
                    timeline_data={"timeline": [{"scene": 7, "duration_seconds": 4}]},
                    prepared_clips_dir=root / "prepared",
                    placeholders_dir=root / "placeholders",
                    output_path=root / "preview.mp4",
                    temp_dir=root / "tmp",
                    concat_list_path=root / "concat.txt",
                    manifest_path=root / "manifest.json",
                    ffmpeg_path="ffmpeg",
                    duration_reader=lambda path: 4.0,
                    runner=lambda command: None,
                    generated_at="2026-05-27T00:00:00Z",
                )

            self.assertIn("escena 7", str(context.exception))

    def test_source_shorter_than_target_fails_before_concat(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared_dir = root / "prepared"
            prepared_dir.mkdir()
            source_path = prepared_dir / "scene_01_ready.mp4"
            source_path.write_bytes(b"short")

            with self.assertRaises(RuntimeError) as context:
                render_preview_video(
                    timeline_data={"timeline": [{"scene": 1, "duration_seconds": 5}]},
                    prepared_clips_dir=prepared_dir,
                    placeholders_dir=root / "placeholders",
                    output_path=root / "preview.mp4",
                    temp_dir=root / "tmp",
                    concat_list_path=root / "concat.txt",
                    manifest_path=root / "manifest.json",
                    ffmpeg_path="ffmpeg",
                    duration_reader=lambda path: 2.0,
                    runner=lambda command: None,
                    generated_at="2026-05-27T00:00:00Z",
                )

            self.assertIn("necesita 5s", str(context.exception))

    def test_invalid_timeline_duration_fails_clearly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared_dir = root / "prepared"
            prepared_dir.mkdir()
            (prepared_dir / "scene_01_ready.mp4").write_bytes(b"video")

            with self.assertRaises(ValueError):
                render_preview_video(
                    timeline_data={"timeline": [{"scene": 1, "duration_seconds": 0}]},
                    prepared_clips_dir=prepared_dir,
                    placeholders_dir=root / "placeholders",
                    output_path=root / "preview.mp4",
                    temp_dir=root / "tmp",
                    concat_list_path=root / "concat.txt",
                    manifest_path=root / "manifest.json",
                    ffmpeg_path="ffmpeg",
                    duration_reader=lambda path: 1.0,
                    runner=lambda command: None,
                    generated_at="2026-05-27T00:00:00Z",
                )

    def test_empty_timeline_fails_clearly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaises(ValueError):
                render_preview_video(
                    timeline_data={"timeline": []},
                    prepared_clips_dir=root / "prepared",
                    placeholders_dir=root / "placeholders",
                    output_path=root / "preview.mp4",
                    temp_dir=root / "tmp",
                    concat_list_path=root / "concat.txt",
                    manifest_path=root / "manifest.json",
                    ffmpeg_path="ffmpeg",
                    duration_reader=lambda path: 1.0,
                    runner=lambda command: None,
                    generated_at="2026-05-27T00:00:00Z",
                )

    def test_fails_clearly_without_ffmpeg(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaises(RuntimeError):
                render_preview_video(
                    timeline_data={"timeline": []},
                    prepared_clips_dir=root / "prepared",
                    placeholders_dir=root / "placeholders",
                    output_path=root / "preview.mp4",
                    temp_dir=root / "tmp",
                    concat_list_path=root / "concat.txt",
                    manifest_path=root / "manifest.json",
                    ffmpeg_path="",
                    duration_reader=lambda path: 1.0,
                    runner=lambda command: None,
                    generated_at="2026-05-27T00:00:00Z",
                )

    def test_build_normalize_command_sets_vertical_format_and_no_audio(self) -> None:
        command = build_ffmpeg_normalize_command(
            ffmpeg_path="ffmpeg",
            source_path=Path("exports/prepared_clips/scene_01_ready.mp4"),
            output_path=Path("exports/render_tmp/scene_01_normalized.mp4"),
            duration_seconds=3,
        )

        self.assertEqual(command[0], "ffmpeg")
        self.assertIn("-vf", command)
        self.assertIn("scale=1080:1920", command[command.index("-vf") + 1])
        self.assertIn("fps=24", command[command.index("-vf") + 1])
        self.assertIn("-t", command)
        self.assertEqual(command[command.index("-t") + 1], "3")
        self.assertIn("-an", command)
        self.assertEqual(command[-1], "exports/render_tmp/scene_01_normalized.mp4")

    def test_build_concat_command_uses_concat_demuxer(self) -> None:
        command = build_ffmpeg_concat_command(
            ffmpeg_path="ffmpeg",
            concat_list_path=Path("exports/concat_list.txt"),
            output_path=Path("exports/preview_video.mp4"),
        )

        self.assertEqual(command[0], "ffmpeg")
        self.assertIn("concat", command)
        self.assertIn("-safe", command)
        self.assertIn("-c", command)
        self.assertEqual(command[command.index("-c") + 1], "copy")
        self.assertEqual(command[-1], "exports/preview_video.mp4")


if __name__ == "__main__":
    unittest.main()
