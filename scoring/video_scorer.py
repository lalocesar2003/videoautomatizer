from copy import deepcopy
from typing import Any


def detect_orientation(width: int, height: int) -> str:
    if height > width:
        return "vertical"
    if width > height:
        return "horizontal"
    return "square"


def score_video_clip(
    *,
    width: int,
    height: int,
    duration: int,
    thumbnail_url: str | None,
    semantic_match: bool = False,
    has_logo_or_text: bool = False,
) -> dict:
    """
    Aplica el scoring definido para clips de B-roll.

    MVP:
    - El scoring técnico sí se calcula.
    - semantic_match y has_logo_or_text quedan preparados para IA/visión después.
    """

    score = 0
    breakdown = {
        "vertical": 0,
        "duration": 0,
        "hd": 0,
        "thumbnail": 0,
        "semantic_match": 0,
        "horizontal_penalty": 0,
        "duration_penalty": 0,
        "logo_text_penalty": 0
    }

    orientation = detect_orientation(width, height)

    if orientation == "vertical":
        breakdown["vertical"] = 40
        score += 40

    if 4 <= duration <= 20:
        breakdown["duration"] = 25
        score += 25

    if width >= 1080 or height >= 1080:
        breakdown["hd"] = 20
        score += 20

    if thumbnail_url:
        breakdown["thumbnail"] = 10
        score += 10

    if semantic_match:
        breakdown["semantic_match"] = 10
        score += 10

    if orientation == "horizontal":
        breakdown["horizontal_penalty"] = -30
        score -= 30

    if duration > 20:
        breakdown["duration_penalty"] = -40
        score -= 40

    if has_logo_or_text:
        breakdown["logo_text_penalty"] = -50
        score -= 50

    return {
        "score": score,
        "orientation": orientation,
        "score_breakdown": breakdown,
        "requires_manual_review": True,
    }


def score_suggestion(suggestion: dict[str, Any]) -> dict[str, Any]:
    scored_suggestion = deepcopy(suggestion)

    score_data = score_video_clip(
        width=int_or_zero(suggestion.get("width")),
        height=int_or_zero(suggestion.get("height")),
        duration=int_or_zero(suggestion.get("duration")),
        thumbnail_url=suggestion.get("thumbnail_url"),
        semantic_match=bool(suggestion.get("semantic_match", False)),
        has_logo_or_text=bool(suggestion.get("has_logo_or_text", False)),
    )

    scored_suggestion.update(score_data)

    return scored_suggestion


def score_pexels_results(pexels_results: dict[str, Any]) -> dict[str, Any]:
    scored_results = {
        "project_title": pexels_results.get("project_title", "Proyecto sin título"),
        "format": pexels_results.get("format", "Vertical"),
        "generated_at": pexels_results.get("generated_at", ""),
        "results": [],
    }

    for scene_result in pexels_results.get("results", []):
        scored_scene = deepcopy(scene_result)
        suggestions = [
            score_suggestion(suggestion)
            for suggestion in scene_result.get("suggestions", [])
        ]
        scored_scene["suggestions"] = sort_by_score(suggestions)
        scored_results["results"].append(scored_scene)

    return scored_results


def sort_by_score(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        suggestions,
        key=lambda suggestion: suggestion.get("score", 0),
        reverse=True,
    )


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
