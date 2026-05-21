import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from panel.results_panel import (
    count_suggestions,
    generate_results_panel,
    render_results_panel,
)


SCORED_RESULTS = {
    "project_title": "El Fin del Excel para Cobrar",
    "format": "Vertical",
    "results": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "visual_intent": "DEJA DE ROGAR POR TU SALDO 📉",
            "query": "person using smartphone",
            "suggestions": [
                {
                    "provider": "pexels",
                    "provider_id": "123",
                    "page_url": "https://www.pexels.com/video/example/",
                    "thumbnail_url": "https://images.pexels.com/thumb.jpg",
                    "preview_url": "https://videos.pexels.com/example.mp4",
                    "duration": 10,
                    "width": 1080,
                    "height": 1920,
                    "orientation": "vertical",
                    "author_name": "Pexels Author",
                    "author_url": "https://www.pexels.com/@author",
                    "score": 95,
                    "score_breakdown": {
                        "vertical": 40,
                        "duration": 25,
                        "hd": 20,
                        "thumbnail": 10,
                    },
                    "requires_manual_review": True,
                }
            ],
        }
    ],
}


class ResultsPanelTests(unittest.TestCase):
    def test_count_suggestions(self) -> None:
        self.assertEqual(count_suggestions(SCORED_RESULTS), 1)

    def test_render_results_panel_contains_required_fields(self) -> None:
        html = render_results_panel(SCORED_RESULTS)

        self.assertIn("El Fin del Excel para Cobrar", html)
        self.assertIn("Escena 1", html)
        self.assertIn("mixed", html)
        self.assertIn("person using smartphone", html)
        self.assertIn("https://images.pexels.com/thumb.jpg", html)
        self.assertIn("Score 95", html)
        self.assertIn("vertical", html)
        self.assertIn("10s", html)
        self.assertIn("1080 × 1920", html)
        self.assertIn("Pexels Author", html)
        self.assertIn("Ver en Pexels", html)
        self.assertIn("Preview", html)
        self.assertIn("Seleccionar", html)
        self.assertIn("Rebuscar", html)

    def test_generate_results_panel_writes_html_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results_panel.html"
            summary = generate_results_panel(SCORED_RESULTS, output_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(summary["scene_count"], 1)
            self.assertEqual(summary["suggestion_count"], 1)
            self.assertIn(
                "Panel simple de revisión",
                output_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
