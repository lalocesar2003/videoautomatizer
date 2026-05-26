import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from missing.missing_scene_detector import detect_missing_scenes


BASE_TIMELINE_ITEM = {
    "scene": 1,
    "start": "0:00",
    "end": "0:03",
    "duration_seconds": 3,
    "asset_type": "mixed",
    "resolution_type": "pexels",
    "primary_action": "Mostrar celular.",
    "message": "",
}


class MissingSceneDetectorTests(unittest.TestCase):
    def test_detects_pending_statuses(self) -> None:
        timeline_data = {
            "project_title": "El Fin del Excel para Cobrar",
            "timeline": [
                build_item(1, "needs_self_recording", "missing_asset"),
                build_item(2, "needs_screen_recording", "missing_asset"),
                build_item(3, "needs_manual_review", "missing_asset"),
                build_item(4, "needs_fallback_search", "fallback_stock"),
                build_item(5, "missing_asset", "missing_asset"),
            ],
        }

        result = detect_missing_scenes(
            timeline_data=timeline_data,
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertEqual(result["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(result["generated_at"], "2026-05-26T00:00:00Z")
        self.assertEqual(len(result["missing_scenes"]), 5)
        self.assertEqual(result["summary"]["blocking_count"], 5)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(
            {item["status"] for item in result["missing_scenes"]},
            {
                "needs_self_recording",
                "needs_screen_recording",
                "needs_manual_review",
                "needs_fallback_search",
                "missing_asset",
            },
        )

    def test_reasons_and_suggested_actions_are_actionable(self) -> None:
        result = detect_missing_scenes(
            timeline_data={"timeline": [build_item(2, "needs_screen_recording")]},
            generated_at="2026-05-26T00:00:00Z",
        )

        missing_scene = result["missing_scenes"][0]

        self.assertEqual(
            missing_scene["reason"],
            "La escena requiere una grabación de pantalla y no tiene asset listo.",
        )
        self.assertEqual(
            missing_scene["suggested_action"],
            "Grabar pantalla o asignar un video local desde el panel.",
        )
        self.assertEqual(missing_scene["severity"], "blocking")
        self.assertEqual(missing_scene["primary_action"], "Mostrar celular.")

    def test_does_not_report_placeholder(self) -> None:
        result = detect_missing_scenes(
            timeline_data={"timeline": [build_item(1, "placeholder", "placeholder")]},
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertEqual(result["missing_scenes"], [])
        self.assertEqual(result["summary"]["missing_count"], 0)

    def test_reports_ready_scene_without_clip_path(self) -> None:
        result = detect_missing_scenes(
            timeline_data={
                "timeline": [
                    build_item(1, "ready", "pexels", clip_path=None),
                ]
            },
            generated_at="2026-05-26T00:00:00Z",
        )

        missing_scene = result["missing_scenes"][0]

        self.assertEqual(missing_scene["scene"], 1)
        self.assertEqual(
            missing_scene["reason"],
            "La escena fue marcada como lista, pero clip_path está vacío.",
        )

    def test_reports_ready_scene_with_missing_clip_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = detect_missing_scenes(
                timeline_data={
                    "timeline": [
                        build_item(
                            1,
                            "ready",
                            "pexels",
                            clip_path="exports/clips/missing.mp4",
                        ),
                    ]
                },
                project_root=Path(temp_dir),
                generated_at="2026-05-26T00:00:00Z",
            )

        missing_scene = result["missing_scenes"][0]

        self.assertEqual(missing_scene["scene"], 1)
        self.assertEqual(
            missing_scene["reason"],
            "La escena fue marcada como lista, pero el archivo indicado en clip_path no existe.",
        )

    def test_does_not_report_ready_scene_with_existing_clip_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip_path = root / "exports" / "clips" / "scene_01_clip_01.mp4"
            clip_path.parent.mkdir(parents=True)
            clip_path.write_bytes(b"video")

            result = detect_missing_scenes(
                timeline_data={
                    "timeline": [
                        build_item(
                            1,
                            "ready",
                            "pexels",
                            clip_path="exports/clips/scene_01_clip_01.mp4",
                        ),
                    ]
                },
                project_root=root,
                generated_at="2026-05-26T00:00:00Z",
            )

        self.assertEqual(result["missing_scenes"], [])

    def test_reports_fallback_stock_with_missing_clip_file(self) -> None:
        result = detect_missing_scenes(
            timeline_data={
                "timeline": [
                    build_item(
                        4,
                        "fallback_stock",
                        "fallback_stock",
                        clip_path="exports/clips/scene_04_clip_01.mp4",
                    )
                ]
            },
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertEqual(result["missing_scenes"][0]["status"], "fallback_stock")
        self.assertEqual(result["summary"]["missing_count"], 1)


def build_item(
    scene: int,
    status: str,
    resolution_type: str = "missing_asset",
    clip_path: str | None = None,
) -> dict:
    item = dict(BASE_TIMELINE_ITEM)
    item.update(
        {
            "scene": scene,
            "status": status,
            "resolution_type": resolution_type,
            "clip_path": clip_path,
        }
    )
    return item


if __name__ == "__main__":
    unittest.main()
