import unittest

from resolution.asset_resolver import resolve_assets


SCENES_DATA = {
    "project_title": "El Fin del Excel para Cobrar",
    "scenes": [
        {"scene": 1, "visual": "Persona con celular.", "text_on_screen": "Cobrar"},
        {"scene": 2, "visual": "Grabar dashboard.", "text_on_screen": "Dashboard"},
        {"scene": 3, "visual": "Salir en cámara.", "text_on_screen": "CTA"},
        {"scene": 4, "visual": "Oficina sin selección.", "text_on_screen": "Stock"},
    ],
}

VISUAL_PLAN_DATA = {
    "visual_plan": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "primary_action": "Persona con celular.",
            "visual_intent": "Cobranza.",
            "search_query_en": "person using smartphone",
        },
        {
            "scene": 2,
            "asset_type": "screen_recording",
            "primary_action": "Grabar dashboard.",
            "visual_intent": "Dashboard.",
            "search_query_en": "",
        },
        {
            "scene": 3,
            "asset_type": "self_recorded",
            "primary_action": "Salir en cámara.",
            "visual_intent": "CTA.",
            "search_query_en": "",
        },
        {
            "scene": 4,
            "asset_type": "stock",
            "primary_action": "Mostrar oficina.",
            "visual_intent": "Oficina.",
            "search_query_en": "business office",
        },
    ]
}

SELECTED_ASSETS_DATA = {
    "selected_assets": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "selection_type": "pexels",
            "selected_clip": {
                "provider": "pexels",
                "provider_id": "clip-1",
                "preview_url": "https://videos.pexels.com/clip-1.mp4",
            },
        },
        {
            "scene": 2,
            "asset_type": "screen_recording",
            "selection_type": "local",
            "selected_clip": {
                "provider": "local",
                "local_path": "local_assets/dashboard.mp4",
            },
        },
    ]
}


class AssetResolverTests(unittest.TestCase):
    def test_resolve_assets_creates_one_resolution_per_scene(self) -> None:
        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data=SELECTED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertEqual(result["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(result["generated_at"], "2026-05-26T00:00:00Z")
        self.assertEqual(len(result["resolved_assets"]), 4)

    def test_pexels_and_local_selections_become_ready(self) -> None:
        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data=SELECTED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )
        resolved_by_scene = index_by_scene(result["resolved_assets"])

        self.assertEqual(resolved_by_scene[1]["resolution_type"], "pexels")
        self.assertEqual(resolved_by_scene[1]["status"], "ready")
        self.assertEqual(
            resolved_by_scene[1]["selected_clip"]["provider_id"],
            "clip-1",
        )

        self.assertEqual(resolved_by_scene[2]["resolution_type"], "local")
        self.assertEqual(resolved_by_scene[2]["status"], "ready")
        self.assertEqual(
            resolved_by_scene[2]["selected_clip"]["local_path"],
            "local_assets/dashboard.mp4",
        )

    def test_missing_self_recorded_and_stock_get_clear_status(self) -> None:
        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data=SELECTED_ASSETS_DATA,
            generated_at="2026-05-26T00:00:00Z",
        )
        resolved_by_scene = index_by_scene(result["resolved_assets"])

        self.assertEqual(resolved_by_scene[3]["resolution_type"], "missing_asset")
        self.assertEqual(resolved_by_scene[3]["status"], "needs_self_recording")
        self.assertIsNone(resolved_by_scene[3]["selected_clip"])

        self.assertEqual(resolved_by_scene[4]["resolution_type"], "missing_asset")
        self.assertEqual(resolved_by_scene[4]["status"], "missing_asset")
        self.assertIsNone(resolved_by_scene[4]["selected_clip"])

    def test_manual_task_becomes_pending_by_asset_type(self) -> None:
        selected_assets_data = {
            "selected_assets": [
                {
                    "scene": 2,
                    "asset_type": "screen_recording",
                    "selection_type": "manual_task",
                    "manual_task": {
                        "primary_action": "Grabar pantalla del dashboard.",
                    },
                }
            ]
        }

        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data=selected_assets_data,
            generated_at="2026-05-26T00:00:00Z",
        )
        resolved_by_scene = index_by_scene(result["resolved_assets"])

        self.assertEqual(resolved_by_scene[2]["resolution_type"], "missing_asset")
        self.assertEqual(resolved_by_scene[2]["status"], "needs_screen_recording")
        self.assertEqual(
            resolved_by_scene[2]["message"],
            "Grabar pantalla del dashboard.",
        )

    def test_placeholder_override_wins_and_does_not_select_clip(self) -> None:
        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data=SELECTED_ASSETS_DATA,
            resolution_choices_data={
                "resolutions": [
                    {
                        "scene": 2,
                        "resolution_type": "placeholder",
                        "message": "Placeholder temporal.",
                    }
                ]
            },
            generated_at="2026-05-26T00:00:00Z",
        )
        resolved_by_scene = index_by_scene(result["resolved_assets"])

        self.assertEqual(resolved_by_scene[2]["resolution_type"], "placeholder")
        self.assertEqual(resolved_by_scene[2]["status"], "placeholder")
        self.assertEqual(resolved_by_scene[2]["message"], "Placeholder temporal.")
        self.assertIsNone(resolved_by_scene[2]["selected_clip"])

    def test_fallback_stock_uses_best_existing_suggestion(self) -> None:
        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data={"selected_assets": []},
            resolution_choices_data={
                "resolutions": [
                    {"scene": 4, "resolution_type": "fallback_stock"}
                ]
            },
            scored_results_data={
                "results": [
                    {
                        "scene": 4,
                        "suggestions": [
                            {"provider": "pexels", "provider_id": "low", "score": 50},
                            {"provider": "pexels", "provider_id": "best", "score": 95},
                        ],
                    }
                ]
            },
            generated_at="2026-05-26T00:00:00Z",
        )
        resolved_by_scene = index_by_scene(result["resolved_assets"])

        self.assertEqual(resolved_by_scene[4]["resolution_type"], "fallback_stock")
        self.assertEqual(resolved_by_scene[4]["status"], "fallback_stock")
        self.assertEqual(resolved_by_scene[4]["selected_clip"]["provider_id"], "best")

    def test_fallback_stock_without_suggestion_marks_needed_search(self) -> None:
        result = resolve_assets(
            scenes_data=SCENES_DATA,
            visual_plan_data=VISUAL_PLAN_DATA,
            selected_assets_data={"selected_assets": []},
            resolution_choices_data={
                "resolutions": [
                    {"scene": 4, "resolution_type": "fallback_stock"}
                ]
            },
            scored_results_data={"results": []},
            generated_at="2026-05-26T00:00:00Z",
        )
        resolved_by_scene = index_by_scene(result["resolved_assets"])

        self.assertEqual(resolved_by_scene[4]["resolution_type"], "fallback_stock")
        self.assertEqual(resolved_by_scene[4]["status"], "needs_fallback_search")
        self.assertIsNone(resolved_by_scene[4]["selected_clip"])

    def test_unknown_resolution_type_fails_clearly(self) -> None:
        with self.assertRaises(ValueError):
            resolve_assets(
                scenes_data=SCENES_DATA,
                visual_plan_data=VISUAL_PLAN_DATA,
                selected_assets_data=SELECTED_ASSETS_DATA,
                resolution_choices_data={
                    "resolutions": [
                        {"scene": 4, "resolution_type": "magic"}
                    ]
                },
                generated_at="2026-05-26T00:00:00Z",
            )


def index_by_scene(items: list[dict]) -> dict[int, dict]:
    return {int(item["scene"]): item for item in items}


if __name__ == "__main__":
    unittest.main()
