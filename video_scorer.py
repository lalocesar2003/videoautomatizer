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
    has_logo_or_text: bool = False
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
        "requires_manual_review": True
    }