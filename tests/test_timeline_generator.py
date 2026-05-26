import unittest

from timeline.timeline_generator import generate_timeline, parse_timecode


SCENES_DATA = {
    "project_title": "El Fin del Excel para Cobrar",
    "scenes": [
        {
            "scene": 2,
            "start": "0:03",
            "end": "0:08",
            "section": "EL PROBLEMA",
            "visual": "Grabar Excel.",
            "text_on_screen": "Excel",
            "audio": "Audio 2",
        },
        {
            "scene": 1,
            "start": "0:00",
            "end": "0:03",
            "section": "EL GANCHO",
            "visual": "Persona con celular.",
            "text_on_screen": "Cobrar",
            "audio": "Audio 1",
        },
        {
            "scene": 3,
            "start": "0:08",
            "end": "0:20",
            "section": "LA SOLUCIÓN",
            "visual": "Grabar dashboard.",
            "text_on_screen": "Dashboard",
            "audio": "Audio 3",
        },
        {
            "scene": 4,
            "start": "0:20",
            "end": "0:32",
            "section": "SEGUIMIENTO",
            "visual": "Usar stock fallback.",
            "text_on_screen": "Stock",
            "audio": "Audio 4",
        },
        {
            "scene": 5,
            "start": "0:32",
            "end": "0:45",
            "section": "CTA",
            "visual": "Salir en cámara.",
            "text_on_screen": "CTA",
            "audio": "Audio 5",
        },
    ],
}

VISUAL_PLAN_DATA = {
    "visual_plan": [
        {"scene": 1, "asset_type": "mixed", "primary_action": "Celular.", "visual_intent": "Cobrar."},
        {"scene": 2, "asset_type": "screen_recording", "primary_action": "Excel.", "visual_intent": "Excel."},
        {"scene": 3, "asset_type": "screen_recording", "primary_action": "Dashboard.", "visual_intent": "Dashboard."},
        {"scene": 4, "asset_type": "stock", "primary_action": "Oficina.", "visual_intent": "Oficina."},
        {"scene": 5, "asset_type": "self_recorded", "primary_action": "CTA.", "visual_intent": "CTA."},
    ]
}

RESOLVED_ASSETS_DATA = {
    "resolved_assets": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "resolution_type": "pexels",
            "status": "ready",
            "message": "Clip Pexels seleccionado.",
            "primary_action": "Resolved action 1",
            "visual_intent": "Resolved intent 1",
            "selected_clip": {"provider": "pexels", "provider_id": "clip-1"},
        },
        {
            "scene": 2,
            "asset_type": "screen_recording",
            "resolution_type": "local",
            "status": "ready",
            "message": "Asset local seleccionado.",
            "selected_clip": {
                "provider": "local",
                "local_path": "local_assets/dashboard.mov",
            },
        },
        {
            "scene": 3,
            "asset_type": "screen_recording",
            "resolution_type": "missing_asset",
            "status": "needs_screen_recording",
            "message": "Grabar pantalla.",
            "selected_clip": None,
        },
        {
            "scene": 4,
            "asset_type": "stock",
            "resolution_type": "fallback_stock",
            "status": "fallback_stock",
            "message": "Stock fallback.",
            "selected_clip": {"provider": "pexels", "provider_id": "fallback"},
        },
        {
            "scene": 5,
            "asset_type": "self_recorded",
            "resolution_type": "placeholder",
            "status": "placeholder",
            "message": "Placeholder temporal.",
            "selected_clip": None,
        },
    ]
}


class TimelineGeneratorTests(unittest.TestCase):
    def test_parse_timecode_supports_minutes_and_hours(self) -> None:
        self.assertEqual(parse_timecode("0:00"), 0)
        self.assertEqual(parse_timecode("0:03"), 3)
        self.assertEqual(parse_timecode("1:05"), 65)
        self.assertEqual(parse_timecode("1:02:03"), 3723)

    def test_generate_timeline_orders_scenes_and_calculates_durations(self) -> None:
        result = generate_timeline(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            resolved_assets_data=RESOLVED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )

        timeline = result["timeline"]

        self.assertEqual([item["scene"] for item in timeline], [1, 2, 3, 4, 5])
        self.assertEqual(timeline[0]["start_seconds"], 0)
        self.assertEqual(timeline[0]["end_seconds"], 3)
        self.assertEqual(timeline[0]["duration_seconds"], 3)
        self.assertEqual(timeline[2]["duration_seconds"], 12)
        self.assertEqual(result["summary"]["total_duration_seconds"], 45)

    def test_ready_assets_get_expected_clip_paths(self) -> None:
        result = generate_timeline(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            resolved_assets_data=RESOLVED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )
        timeline_by_scene = index_by_scene(result["timeline"])

        self.assertEqual(
            timeline_by_scene[1]["clip_path"],
            "exports/clips/scene_01_clip_01.mp4",
        )
        self.assertEqual(
            timeline_by_scene[2]["clip_path"],
            "exports/clips/scene_02_clip_01.mov",
        )
        self.assertEqual(
            timeline_by_scene[4]["clip_path"],
            "exports/clips/scene_04_clip_01.mp4",
        )

    def test_pending_and_placeholder_scenes_have_no_clip_path(self) -> None:
        result = generate_timeline(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            resolved_assets_data=RESOLVED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )
        timeline_by_scene = index_by_scene(result["timeline"])

        self.assertIsNone(timeline_by_scene[3]["clip_path"])
        self.assertEqual(timeline_by_scene[3]["status"], "needs_screen_recording")
        self.assertIsNone(timeline_by_scene[5]["clip_path"])
        self.assertEqual(timeline_by_scene[5]["status"], "placeholder")

    def test_timeline_preserves_scene_context_and_resolved_messages(self) -> None:
        result = generate_timeline(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            resolved_assets_data=RESOLVED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )
        scene_1 = result["timeline"][0]

        self.assertEqual(scene_1["section"], "EL GANCHO")
        self.assertEqual(scene_1["text_on_screen"], "Cobrar")
        self.assertEqual(scene_1["audio"], "Audio 1")
        self.assertEqual(scene_1["primary_action"], "Resolved action 1")
        self.assertEqual(scene_1["visual_intent"], "Resolved intent 1")
        self.assertEqual(scene_1["message"], "Clip Pexels seleccionado.")

    def test_summary_counts_ready_and_pending_items(self) -> None:
        result = generate_timeline(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            resolved_assets_data=RESOLVED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertEqual(
            result["summary"],
            {
                "scene_count": 5,
                "ready_count": 4,
                "pending_count": 1,
                "total_duration_seconds": 45,
            },
        )

    def test_invalid_duration_fails_clearly(self) -> None:
        scenes_data = {
            "scenes": [
                {
                    "scene": 1,
                    "start": "0:03",
                    "end": "0:03",
                }
            ]
        }

        with self.assertRaises(ValueError):
            generate_timeline(
                scenes_data=scenes_data,
                visual_plan_data={"visual_plan": []},
                resolved_assets_data={"resolved_assets": []},
                generated_at="2026-05-26T00:00:00Z",
            )

    def test_invalid_timecode_fails_clearly(self) -> None:
        with self.assertRaises(ValueError):
            parse_timecode("1:75")


def index_by_scene(items: list[dict]) -> dict[int, dict]:
    return {int(item["scene"]): item for item in items}


if __name__ == "__main__":
    unittest.main()
