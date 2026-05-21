import unittest

from scoring.video_scorer import (
    detect_orientation,
    score_pexels_results,
    score_suggestion,
    score_video_clip,
)


PEXELS_RESULTS = {
    "project_title": "El Fin del Excel para Cobrar",
    "format": "Vertical",
    "generated_at": "2026-05-21T00:00:00+00:00",
    "results": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "visual_intent": "DEJA DE ROGAR POR TU SALDO 📉",
            "query": "person using smartphone",
            "suggestions": [
                {
                    "provider": "pexels",
                    "provider_id": "vertical-good",
                    "page_url": "https://example.com/good",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                    "preview_url": "https://example.com/video.mp4",
                    "duration": 10,
                    "width": 1080,
                    "height": 1920,
                    "orientation": "vertical",
                    "author_name": "Author",
                    "author_url": "https://example.com/author",
                },
                {
                    "provider": "pexels",
                    "provider_id": "horizontal-long",
                    "page_url": "https://example.com/bad",
                    "thumbnail_url": "",
                    "preview_url": "https://example.com/video-2.mp4",
                    "duration": 40,
                    "width": 1920,
                    "height": 1080,
                    "orientation": "horizontal",
                    "author_name": "Author",
                    "author_url": "https://example.com/author",
                },
            ],
        }
    ],
}


class VideoScorerTests(unittest.TestCase):
    def test_detect_orientation(self) -> None:
        self.assertEqual(detect_orientation(1080, 1920), "vertical")
        self.assertEqual(detect_orientation(1920, 1080), "horizontal")
        self.assertEqual(detect_orientation(1000, 1000), "square")

    def test_score_video_clip_scores_good_vertical_clip(self) -> None:
        result = score_video_clip(
            width=1080,
            height=1920,
            duration=10,
            thumbnail_url="https://example.com/thumb.jpg",
            semantic_match=True,
        )

        self.assertEqual(result["score"], 105)
        self.assertEqual(result["orientation"], "vertical")
        self.assertEqual(result["score_breakdown"]["vertical"], 40)
        self.assertEqual(result["score_breakdown"]["semantic_match"], 10)
        self.assertTrue(result["requires_manual_review"])

    def test_score_video_clip_penalizes_horizontal_long_clip(self) -> None:
        result = score_video_clip(
            width=1920,
            height=1080,
            duration=40,
            thumbnail_url="",
            has_logo_or_text=True,
        )

        self.assertEqual(result["score"], -100)
        self.assertEqual(result["orientation"], "horizontal")
        self.assertEqual(result["score_breakdown"]["horizontal_penalty"], -30)
        self.assertEqual(result["score_breakdown"]["duration_penalty"], -40)
        self.assertEqual(result["score_breakdown"]["logo_text_penalty"], -50)

    def test_score_suggestion_adds_scoring_fields(self) -> None:
        suggestion = PEXELS_RESULTS["results"][0]["suggestions"][0]
        scored = score_suggestion(suggestion)

        self.assertEqual(scored["score"], 95)
        self.assertEqual(scored["orientation"], "vertical")
        self.assertIn("score_breakdown", scored)
        self.assertIn("requires_manual_review", scored)

    def test_score_pexels_results_preserves_structure_and_sorts(self) -> None:
        scored_results = score_pexels_results(PEXELS_RESULTS)
        suggestions = scored_results["results"][0]["suggestions"]

        self.assertEqual(scored_results["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(scored_results["results"][0]["scene"], 1)
        self.assertEqual(suggestions[0]["provider_id"], "vertical-good")
        self.assertGreater(suggestions[0]["score"], suggestions[1]["score"])


if __name__ == "__main__":
    unittest.main()
