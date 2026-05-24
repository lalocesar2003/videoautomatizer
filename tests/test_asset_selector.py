import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from selection.asset_selector import (
    build_selected_assets,
    build_selected_assets_from_scene_choices,
    count_suggestions,
    get_choices_by_scene,
    get_selected_provider_ids,
    load_json,
    save_selected_assets,
)


SCORED_RESULTS = {
    "project_title": "El Fin del Excel para Cobrar",
    "results": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "visual_intent": "Persona frustrada usando celular.",
            "query": "person using smartphone",
            "suggestions": [
                {
                    "provider": "pexels",
                    "provider_id": "clip-1",
                    "page_url": "https://pexels.com/video/clip-1",
                    "preview_url": "https://videos.pexels.com/clip-1.mp4",
                    "thumbnail_url": "https://images.pexels.com/clip-1.jpg",
                    "duration": 10,
                    "width": 1080,
                    "height": 1920,
                    "orientation": "vertical",
                    "author_name": "Autor 1",
                    "score": 95,
                    "score_breakdown": {"vertical": 40},
                },
                {
                    "provider": "pexels",
                    "provider_id": "clip-2",
                    "page_url": "https://pexels.com/video/clip-2",
                    "preview_url": "https://videos.pexels.com/clip-2.mp4",
                    "thumbnail_url": "https://images.pexels.com/clip-2.jpg",
                    "duration": 22,
                    "width": 1080,
                    "height": 1920,
                    "orientation": "vertical",
                    "author_name": "Autor 2",
                    "score": 55,
                    "score_breakdown": {"duration_penalty": -40},
                },
            ],
        }
    ],
}


class AssetSelectorTests(unittest.TestCase):
    def test_count_suggestions(self) -> None:
        self.assertEqual(count_suggestions(SCORED_RESULTS), 2)

    def test_build_selected_assets_keeps_only_selected_clips(self) -> None:
        result = build_selected_assets(SCORED_RESULTS, {"clip-1"})

        self.assertEqual(result["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(len(result["selected_assets"]), 1)

        selected = result["selected_assets"][0]
        self.assertEqual(selected["scene"], 1)
        self.assertEqual(selected["asset_type"], "mixed")
        self.assertEqual(selected["query"], "person using smartphone")
        self.assertEqual(selected["selected_clip"]["provider_id"], "clip-1")
        self.assertEqual(selected["selected_clip"]["score"], 95)

    def test_get_selected_provider_ids_reads_selection(self) -> None:
        selected_assets = build_selected_assets(SCORED_RESULTS, {"clip-1"})

        self.assertEqual(get_selected_provider_ids(selected_assets), {"clip-1"})

    def test_build_selected_assets_from_scene_choices_allows_one_asset_per_scene(self) -> None:
        scenes = [
            {"scene": 1, "visual": "Persona usando celular."},
            {"scene": 2, "visual": "Grabar pantalla del dashboard."},
        ]
        visual_plan_by_scene = {
            1: {
                "asset_type": "mixed",
                "visual_intent": "Persona frustrada usando celular.",
                "search_query_en": "person using smartphone",
                "primary_action": "Mostrar frustración con celular.",
            },
            2: {
                "asset_type": "screen_recording",
                "visual_intent": "Mostrar dashboard.",
                "search_query_en": "",
                "primary_action": "Grabar pantalla del dashboard.",
            },
        }
        scored_results_by_scene = {
            1: SCORED_RESULTS["results"][0],
        }

        result = build_selected_assets_from_scene_choices(
            project_title="El Fin del Excel para Cobrar",
            scenes=scenes,
            visual_plan_by_scene=visual_plan_by_scene,
            scored_results_by_scene=scored_results_by_scene,
            choices_by_scene={
                1: "clip-2",
                2: "manual_task",
            },
        )

        self.assertEqual(len(result["selected_assets"]), 2)
        self.assertEqual(result["selected_assets"][0]["scene"], 1)
        self.assertEqual(result["selected_assets"][0]["selection_type"], "pexels")
        self.assertEqual(
            result["selected_assets"][0]["selected_clip"]["provider_id"],
            "clip-2",
        )

        self.assertEqual(result["selected_assets"][1]["scene"], 2)
        self.assertEqual(result["selected_assets"][1]["selection_type"], "manual_task")
        self.assertEqual(
            result["selected_assets"][1]["manual_task"]["task_type"],
            "screen_recording",
        )

    def test_get_choices_by_scene_reads_manual_task_and_pexels(self) -> None:
        selected_assets = {
            "selected_assets": [
                {
                    "scene": 1,
                    "selection_type": "pexels",
                    "selected_clip": {"provider_id": "clip-1"},
                },
                {
                    "scene": 2,
                    "selection_type": "manual_task",
                    "manual_task": {"task_type": "screen_recording"},
                },
            ],
        }

        self.assertEqual(
            get_choices_by_scene(selected_assets),
            {
                1: "clip-1",
                2: "manual_task",
            },
        )

    def test_save_and_load_selected_assets(self) -> None:
        selected_assets = build_selected_assets(SCORED_RESULTS, {"clip-1"})

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "selected_assets.json"
            save_selected_assets(path, selected_assets)

            self.assertTrue(path.exists())
            self.assertEqual(load_json(path), selected_assets)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                selected_assets,
            )


if __name__ == "__main__":
    unittest.main()
