import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from placeholders.placeholder_generator import (
    build_placeholder_filename,
    build_placeholder_text,
    generate_placeholders,
)


MISSING_SCENES_DATA = {
    "project_title": "El Fin del Excel para Cobrar",
    "missing_scenes": [
        {
            "scene": 3,
            "start": "0:08",
            "end": "0:20",
            "duration_seconds": 12,
            "asset_type": "screen_recording",
            "status": "needs_screen_recording",
            "reason": "La escena requiere una grabación de pantalla.",
            "primary_action": "Grabar dashboard de SusyCafe.",
        },
        {
            "scene": 5,
            "start": "0:32",
            "end": "0:45",
            "duration_seconds": 13,
            "asset_type": "self_recorded",
            "status": "needs_self_recording",
            "reason": "La escena requiere grabación del creador.",
            "primary_action": "Grabar CTA mirando a cámara.",
        },
    ],
}

TIMELINE_DATA = {
    "timeline": [
        {
            "scene": 3,
            "duration_seconds": 12,
            "asset_type": "screen_recording",
            "status": "needs_screen_recording",
            "primary_action": "Grabar dashboard de SusyCafe.",
        },
        {
            "scene": 5,
            "duration_seconds": 13,
            "asset_type": "self_recorded",
            "status": "needs_self_recording",
            "primary_action": "Grabar CTA mirando a cámara.",
        },
    ]
}


class PlaceholderGeneratorTests(unittest.TestCase):
    def test_build_placeholder_filename(self) -> None:
        self.assertEqual(build_placeholder_filename(3), "scene_03_placeholder.mp4")
        self.assertEqual(build_placeholder_filename(12), "scene_12_placeholder.mp4")

    def test_generate_placeholders_creates_files_and_manifest(self) -> None:
        commands = []

        def fake_runner(command: list[str]) -> None:
            commands.append(command)
            Path(command[-1]).write_bytes(b"video")

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports" / "placeholders"
            manifest = generate_placeholders(
                missing_scenes_data=MISSING_SCENES_DATA,
                timeline_data=TIMELINE_DATA,
                output_dir=output_dir,
                ffmpeg_path="ffmpeg",
                runner=fake_runner,
                generated_at="2026-05-26T00:00:00Z",
            )

            self.assertEqual(manifest["project_title"], "El Fin del Excel para Cobrar")
            self.assertEqual(manifest["generated_at"], "2026-05-26T00:00:00Z")
            self.assertEqual(manifest["summary"]["placeholder_count"], 2)
            self.assertEqual(manifest["summary"]["total_duration_seconds"], 25)

            self.assertTrue((output_dir / "scene_03_placeholder.mp4").exists())
            self.assertTrue((output_dir / "scene_05_placeholder.mp4").exists())
            self.assertTrue((output_dir / "placeholder_manifest.json").exists())
            self.assertEqual(len(commands), 2)

            saved_manifest = json.loads(
                (output_dir / "placeholder_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved_manifest, manifest)

    def test_ffmpeg_command_uses_duration_and_output_path(self) -> None:
        commands = []

        def fake_runner(command: list[str]) -> None:
            commands.append(command)
            Path(command[-1]).write_bytes(b"video")

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "placeholders"
            generate_placeholders(
                missing_scenes_data={
                    "missing_scenes": [MISSING_SCENES_DATA["missing_scenes"][0]]
                },
                timeline_data=TIMELINE_DATA,
                output_dir=output_dir,
                ffmpeg_path="ffmpeg",
                runner=fake_runner,
                generated_at="2026-05-26T00:00:00Z",
            )

        command = commands[0]
        self.assertIn("-t", command)
        self.assertEqual(command[command.index("-t") + 1], "12")
        self.assertEqual(command[-1].endswith("scene_03_placeholder.mp4"), True)
        self.assertIn("-loop", command)
        self.assertIn("-i", command)
        self.assertTrue(command[command.index("-i") + 1].endswith(".ppm"))

    def test_uses_timeline_duration_when_missing_scene_has_no_duration(self) -> None:
        commands = []
        missing_scenes_data = {
            "missing_scenes": [
                {
                    "scene": 3,
                    "asset_type": "screen_recording",
                    "status": "needs_screen_recording",
                    "primary_action": "Grabar dashboard.",
                }
            ]
        }

        def fake_runner(command: list[str]) -> None:
            commands.append(command)
            Path(command[-1]).write_bytes(b"video")

        with TemporaryDirectory() as temp_dir:
            generate_placeholders(
                missing_scenes_data=missing_scenes_data,
                timeline_data=TIMELINE_DATA,
                output_dir=Path(temp_dir),
                ffmpeg_path="ffmpeg",
                runner=fake_runner,
                generated_at="2026-05-26T00:00:00Z",
            )

        command = commands[0]
        self.assertEqual(command[command.index("-t") + 1], "12")

    def test_rejects_invalid_duration(self) -> None:
        missing_scenes_data = {
            "missing_scenes": [
                {
                    "scene": 9,
                    "duration_seconds": 0,
                    "asset_type": "screen_recording",
                    "status": "needs_screen_recording",
                }
            ]
        }

        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                generate_placeholders(
                    missing_scenes_data=missing_scenes_data,
                    timeline_data={"timeline": []},
                    output_dir=Path(temp_dir),
                    ffmpeg_path="ffmpeg",
                    runner=lambda command: None,
                    generated_at="2026-05-26T00:00:00Z",
                )

    def test_fails_clearly_without_ffmpeg(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(RuntimeError):
                generate_placeholders(
                    missing_scenes_data=MISSING_SCENES_DATA,
                    timeline_data=TIMELINE_DATA,
                    output_dir=Path(temp_dir),
                    ffmpeg_path="",
                    runner=lambda command: None,
                    generated_at="2026-05-26T00:00:00Z",
                )

    def test_placeholder_text_contains_scene_context(self) -> None:
        text = build_placeholder_text(
            missing_scene=MISSING_SCENES_DATA["missing_scenes"][0],
            timeline_item=TIMELINE_DATA["timeline"][0],
            duration_seconds=12,
        )

        self.assertIn("ESCENA 3 FALTANTE", text)
        self.assertIn("Tipo: screen_recording", text)
        self.assertIn("Estado: needs_screen_recording", text)
        self.assertIn("Duración: 12 segundos", text)
        self.assertIn("Grabar dashboard", text)
        self.assertIn("SusyCafe", text)


if __name__ == "__main__":
    unittest.main()
