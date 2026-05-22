import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from selection.asset_selector import (
    build_selected_assets,
    count_suggestions,
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
