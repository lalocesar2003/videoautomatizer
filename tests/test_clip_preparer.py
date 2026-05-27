import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from preparation.clip_preparer import (
    build_ffmpeg_prepare_command,
    build_ready_filename,
    prepare_clips,
)


class ClipPreparerTests(unittest.TestCase):
    def test_build_ready_filename(self) -> None:
        self.assertEqual(build_ready_filename(1), "scene_01_ready.mp4")
        self.assertEqual(build_ready_filename(12), "scene_12_ready.mp4")

    def test_prepare_clips_trims_real_clip_and_uses_placeholder(self) -> None:
        commands = []

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clips_dir = root / "exports" / "clips"
            placeholders_dir = root / "exports" / "placeholders"
            output_dir = root / "exports" / "prepared_clips"
            clips_dir.mkdir(parents=True)
            placeholders_dir.mkdir(parents=True)

            clip_path = clips_dir / "scene_01_clip_01.mp4"
            placeholder_path = placeholders_dir / "scene_02_placeholder.mp4"
            clip_path.write_bytes(b"clip")
            placeholder_path.write_bytes(b"placeholder")

            timeline_data = {
                "project_title": "Proyecto Test",
                "timeline": [
                    {
                        "scene": 2,
                        "duration_seconds": 5,
                        "asset_type": "screen_recording",
                        "status": "needs_screen_recording",
                        "clip_path": None,
                    },
                    {
                        "scene": 1,
                        "duration_seconds": 3,
                        "asset_type": "mixed",
                        "status": "ready",
                        "clip_path": str(clip_path),
                    },
                ],
            }

            durations = {
                "scene_01_clip_01.mp4": 10.0,
                "scene_02_placeholder.mp4": 5.0,
            }

            def fake_duration_reader(path: Path) -> float:
                return durations[path.name]

            def fake_runner(command: list[str]) -> None:
                commands.append(command)
                Path(command[-1]).write_bytes(b"ready")

            manifest = prepare_clips(
                timeline_data=timeline_data,
                clips_dir=clips_dir,
                placeholders_dir=placeholders_dir,
                output_dir=output_dir,
                ffmpeg_path="ffmpeg",
                duration_reader=fake_duration_reader,
                runner=fake_runner,
                generated_at="2026-05-26T00:00:00Z",
            )

            self.assertEqual(manifest["project_title"], "Proyecto Test")
            self.assertEqual(manifest["generated_at"], "2026-05-26T00:00:00Z")
            self.assertEqual(manifest["summary"]["scene_count"], 2)
            self.assertEqual(manifest["summary"]["prepared_count"], 2)
            self.assertEqual(manifest["summary"]["warning_count"], 0)
            self.assertEqual(manifest["summary"]["total_duration_seconds"], 8)

            prepared_by_scene = {
                item["scene"]: item for item in manifest["prepared_clips"]
            }
            self.assertEqual(prepared_by_scene[1]["strategy"], "trim")
            self.assertEqual(prepared_by_scene[2]["strategy"], "placeholder")
            self.assertEqual(prepared_by_scene[1]["duration_seconds"], 3)
            self.assertEqual(prepared_by_scene[2]["duration_seconds"], 5)

            self.assertTrue((output_dir / "scene_01_ready.mp4").exists())
            self.assertTrue((output_dir / "scene_02_ready.mp4").exists())
            self.assertTrue((output_dir / "prepared_manifest.json").exists())
            self.assertEqual(len(commands), 2)

            saved_manifest = json.loads(
                (output_dir / "prepared_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved_manifest, manifest)

    def test_missing_clip_path_uses_placeholder_and_reports_warning(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clips_dir = root / "exports" / "clips"
            placeholders_dir = root / "exports" / "placeholders"
            output_dir = root / "exports" / "prepared_clips"
            clips_dir.mkdir(parents=True)
            placeholders_dir.mkdir(parents=True)

            placeholder_path = placeholders_dir / "scene_01_placeholder.mp4"
            placeholder_path.write_bytes(b"placeholder")

            timeline_data = {
                "timeline": [
                    {
                        "scene": 1,
                        "duration_seconds": 3,
                        "asset_type": "mixed",
                        "status": "ready",
                        "clip_path": str(clips_dir / "missing.mp4"),
                    }
                ]
            }

            manifest = prepare_clips(
                timeline_data=timeline_data,
                clips_dir=clips_dir,
                placeholders_dir=placeholders_dir,
                output_dir=output_dir,
                ffmpeg_path="ffmpeg",
                duration_reader=lambda path: 3.0,
                runner=lambda command: Path(command[-1]).write_bytes(b"ready"),
                generated_at="2026-05-26T00:00:00Z",
            )

            self.assertEqual(manifest["summary"]["prepared_count"], 1)
            self.assertEqual(manifest["summary"]["warning_count"], 1)
            self.assertEqual(manifest["prepared_clips"][0]["strategy"], "placeholder")
            self.assertIn("clip_path", manifest["warnings"][0]["reason"])

    def test_short_clip_uses_placeholder_and_reports_warning(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clips_dir = root / "exports" / "clips"
            placeholders_dir = root / "exports" / "placeholders"
            output_dir = root / "exports" / "prepared_clips"
            clips_dir.mkdir(parents=True)
            placeholders_dir.mkdir(parents=True)

            clip_path = clips_dir / "scene_01_clip_01.mp4"
            placeholder_path = placeholders_dir / "scene_01_placeholder.mp4"
            clip_path.write_bytes(b"clip")
            placeholder_path.write_bytes(b"placeholder")

            durations = {
                "scene_01_clip_01.mp4": 2.0,
                "scene_01_placeholder.mp4": 5.0,
            }

            manifest = prepare_clips(
                timeline_data={
                    "timeline": [
                        {
                            "scene": 1,
                            "duration_seconds": 5,
                            "asset_type": "stock",
                            "status": "ready",
                            "clip_path": str(clip_path),
                        }
                    ]
                },
                clips_dir=clips_dir,
                placeholders_dir=placeholders_dir,
                output_dir=output_dir,
                ffmpeg_path="ffmpeg",
                duration_reader=lambda path: durations[path.name],
                runner=lambda command: Path(command[-1]).write_bytes(b"ready"),
                generated_at="2026-05-26T00:00:00Z",
            )

            self.assertEqual(manifest["summary"]["prepared_count"], 1)
            self.assertEqual(manifest["summary"]["warning_count"], 1)
            self.assertEqual(manifest["prepared_clips"][0]["strategy"], "placeholder")
            self.assertIn("más corto", manifest["warnings"][0]["reason"])

    def test_short_clip_without_placeholder_needs_manual_review(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clips_dir = root / "exports" / "clips"
            placeholders_dir = root / "exports" / "placeholders"
            output_dir = root / "exports" / "prepared_clips"
            clips_dir.mkdir(parents=True)
            placeholders_dir.mkdir(parents=True)

            clip_path = clips_dir / "scene_01_clip_01.mp4"
            clip_path.write_bytes(b"clip")

            manifest = prepare_clips(
                timeline_data={
                    "timeline": [
                        {
                            "scene": 1,
                            "duration_seconds": 5,
                            "asset_type": "stock",
                            "status": "ready",
                            "clip_path": str(clip_path),
                        }
                    ]
                },
                clips_dir=clips_dir,
                placeholders_dir=placeholders_dir,
                output_dir=output_dir,
                ffmpeg_path="ffmpeg",
                duration_reader=lambda path: 2.0,
                runner=lambda command: Path(command[-1]).write_bytes(b"ready"),
                generated_at="2026-05-26T00:00:00Z",
            )

            self.assertEqual(manifest["summary"]["prepared_count"], 0)
            self.assertEqual(manifest["summary"]["warning_count"], 1)
            self.assertEqual(manifest["warnings"][0]["status"], "needs_manual_review")
            self.assertFalse((output_dir / "scene_01_ready.mp4").exists())

    def test_invalid_duration_fails_clearly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                prepare_clips(
                    timeline_data={"timeline": [{"scene": 9, "duration_seconds": 0}]},
                    clips_dir=Path(temp_dir) / "clips",
                    placeholders_dir=Path(temp_dir) / "placeholders",
                    output_dir=Path(temp_dir) / "prepared",
                    ffmpeg_path="ffmpeg",
                    duration_reader=lambda path: 3.0,
                    runner=lambda command: None,
                    generated_at="2026-05-26T00:00:00Z",
                )

    def test_fails_clearly_without_ffmpeg(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(RuntimeError):
                prepare_clips(
                    timeline_data={"timeline": []},
                    clips_dir=Path(temp_dir) / "clips",
                    placeholders_dir=Path(temp_dir) / "placeholders",
                    output_dir=Path(temp_dir) / "prepared",
                    ffmpeg_path="",
                    duration_reader=lambda path: 3.0,
                    runner=lambda command: None,
                    generated_at="2026-05-26T00:00:00Z",
                )

    def test_build_ffmpeg_command_uses_duration_and_output(self) -> None:
        command = build_ffmpeg_prepare_command(
            ffmpeg_path="ffmpeg",
            source_path=Path("exports/clips/source.mov"),
            output_path=Path("exports/prepared_clips/scene_01_ready.mp4"),
            duration_seconds=3,
        )

        self.assertEqual(command[0], "ffmpeg")
        self.assertIn("-i", command)
        self.assertEqual(command[command.index("-i") + 1], "exports/clips/source.mov")
        self.assertIn("-t", command)
        self.assertEqual(command[command.index("-t") + 1], "3")
        self.assertIn("-an", command)
        self.assertEqual(command[-1], "exports/prepared_clips/scene_01_ready.mp4")


if __name__ == "__main__":
    unittest.main()
