import os
import unittest
from unittest.mock import patch

from providers.pexels_provider import (
    build_pexels_http_error,
    detect_orientation,
    normalize_pexels_videos,
    read_env_value,
    search_pexels_for_visual_plan,
)


VISUAL_PLAN = {
    "project_title": "El Fin del Excel para Cobrar",
    "format": "Vertical",
    "visual_plan": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "needs_pexels": True,
            "visual_intent": "DEJA DE ROGAR POR TU SALDO 📉",
            "search_query_en": "person using smartphone",
        },
        {
            "scene": 2,
            "asset_type": "screen_recording",
            "needs_pexels": False,
            "visual_intent": "El Excel oculta tus deudas.",
            "search_query_en": "",
        },
    ],
}


PEXELS_RESPONSE = {
    "videos": [
        {
            "id": 123,
            "url": "https://www.pexels.com/video/example/",
            "duration": 8,
            "width": 1080,
            "height": 1920,
            "image": "https://images.pexels.com/example.jpg",
            "user": {
                "name": "Pexels Author",
                "url": "https://www.pexels.com/@author/",
            },
            "video_files": [
                {
                    "width": 540,
                    "height": 960,
                    "link": "https://videos.pexels.com/small.mp4",
                },
                {
                    "width": 1080,
                    "height": 1920,
                    "link": "https://videos.pexels.com/large.mp4",
                },
            ],
            "video_pictures": [
                {"picture": "https://images.pexels.com/thumb.jpg"},
            ],
        }
    ]
}


class PexelsProviderTests(unittest.TestCase):
    def test_search_pexels_only_searches_needed_scenes(self) -> None:
        calls = []

        def fake_get(url, headers):
            calls.append((url, headers))
            return PEXELS_RESPONSE

        with patch.dict(os.environ, {"PEXELS_API_KEY": "test-key"}):
            result = search_pexels_for_visual_plan(VISUAL_PLAN, http_get=fake_get)

        self.assertEqual(result["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(result["format"], "Vertical")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(len(calls), 1)

        url, headers = calls[0]
        self.assertIn("query=person+using+smartphone", url)
        self.assertIn("orientation=portrait", url)
        self.assertEqual(headers["Authorization"], "test-key")
        self.assertEqual(headers["Accept"], "application/json")

        scene_result = result["results"][0]
        self.assertEqual(scene_result["scene"], 1)
        self.assertEqual(scene_result["query"], "person using smartphone")
        self.assertEqual(scene_result["suggestions"][0]["provider"], "pexels")

    def test_normalize_pexels_videos_extracts_expected_fields(self) -> None:
        suggestions = normalize_pexels_videos(PEXELS_RESPONSE["videos"])

        self.assertEqual(suggestions[0]["provider_id"], "123")
        self.assertEqual(suggestions[0]["preview_url"], "https://videos.pexels.com/large.mp4")
        self.assertEqual(suggestions[0]["thumbnail_url"], "https://images.pexels.com/thumb.jpg")
        self.assertEqual(suggestions[0]["orientation"], "vertical")
        self.assertEqual(suggestions[0]["author_name"], "Pexels Author")

    def test_detect_orientation(self) -> None:
        self.assertEqual(detect_orientation(1080, 1920), "vertical")
        self.assertEqual(detect_orientation(1920, 1080), "horizontal")
        self.assertEqual(detect_orientation(1000, 1000), "square")

    def test_missing_api_key_has_clear_error(self) -> None:
        with patch.dict(os.environ, {"PEXELS_API_KEY": "tu_api_key_aqui"}):
            with self.assertRaises(RuntimeError):
                search_pexels_for_visual_plan(VISUAL_PLAN, http_get=lambda url, headers: {})

    def test_read_env_value_reads_simple_env_file(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("PEXELS_API_KEY='local-key'\n", encoding="utf-8")

            self.assertEqual(read_env_value("PEXELS_API_KEY", env_path), "local-key")

    def test_build_pexels_http_error_explains_auth_and_limits(self) -> None:
        auth_error = build_pexels_http_error(403, "forbidden")
        limit_error = build_pexels_http_error(429, "too many requests")

        self.assertIn("PEXELS_API_KEY", auth_error)
        self.assertIn("límite", limit_error)


if __name__ == "__main__":
    unittest.main()
