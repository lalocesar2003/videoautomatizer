import re
from typing import Any


FIELD_LABELS = {
    "visual": r"Visual(?:\s*\([^)]*\))?",
    "audio": r"Audio(?:\s*\([^)]*\))?",
    "text_on_screen": r"Texto\s+en\s+pantalla(?:\s*/\s*FX)?(?:\s*\([^)]*\))?",
    "fx": r"FX(?:\s*\([^)]*\))?",
    "editing_notes": r"Notas\s+edici[oó]n",
    "section": r"Secci[oó]n",
    "time": r"Tiempo",
    "style_text": r"Estilo\s+texto",
    "tone_audio": r"Tono(?:\s+audio)?",
}

ALL_LABELS_REGEX = "|".join(FIELD_LABELS.values())


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.strip()
    value = value.replace("\t", " ")
    value = re.sub(r"[ \u00A0]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)

    # Quitar comillas envolventes simples si existen
    if len(value) >= 2 and value[0] in ['"', "“"] and value[-1] in ['"', "”"]:
        value = value[1:-1].strip()

    return value


def extract_title(script_text: str) -> str:
    patterns = [
        r'^\s*#\s*Guion\s+para\s+.+?:\s*"?(.+?)"?\s*$',
        r'^\s*Guion\s+para\s+.+?:\s*"?(.+?)"?\s*$',
        r'^\s*🎬\s*Guion\s+T[eé]cnico:\s*"?(.+?)"?\s*$',
    ]

    for pattern in patterns:
        match = re.search(pattern, script_text, re.IGNORECASE | re.MULTILINE)
        if match:
            return clean_text(match.group(1))

    return "Proyecto sin título"


def extract_metadata(script_text: str) -> dict[str, str]:
    metadata = {}

    metadata_fields = {
        "platform": r"Plataforma",
        "format": r"Formato",
        "target_duration": r"Duraci[oó]n\s+objetivo",
        "visual_style": r"Estilo\s+visual",
        "objective": r"Objetivo(?:\s+del\s+video)?",
    }

    for key, label in metadata_fields.items():
        pattern = rf"^\s*{label}\s*:\s*(.+?)\s*$"
        match = re.search(pattern, script_text, re.IGNORECASE | re.MULTILINE)
        metadata[key] = clean_text(match.group(1)) if match else ""

    return metadata


def extract_field(block: str, field_key: str) -> str:
    label_regex = FIELD_LABELS[field_key]

    pattern = re.compile(
        rf"""
        (?:^|\n)
        \s*
        (?:[-*•]\s*)?
        {label_regex}
        \s*:
        \s*
        (?P<value>.*?)
        (?=
            \n\s*(?:[-*•]\s*)?(?:{ALL_LABELS_REGEX})\s*:
            |
            \Z
        )
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    match = pattern.search(block)

    if not match:
        return ""

    return clean_text(match.group("value"))


def parse_time_range(time_text: str) -> tuple[str, str]:
    match = re.search(
        r"(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})",
        time_text,
    )

    if not match:
        return "", ""

    return match.group("start"), match.group("end")


def parse_bracket_scene_blocks(script_text: str) -> list[dict[str, Any]]:
    """
    Parser para formato tipo:

    [0:00 - 0:03] EL GANCHO (HOOK)
    • Visual: ...
    • Texto en pantalla: ...
    • Audio: ...
    """

    pattern = re.compile(
        r"""
        ^\s*
        \[
            (?P<start>\d{1,2}:\d{2})
            \s*-\s*
            (?P<end>\d{1,2}:\d{2})
        \]
        \s*
        (?P<section>.+?)
        \s*$
        (?P<body>.*?)
        (?=
            ^\s*\[\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\]
            |
            \Z
        )
        """,
        re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
    )

    scenes = []

    for index, match in enumerate(pattern.finditer(script_text), start=1):
        body = match.group("body").strip()

        scene = {
            "scene": index,
            "start": clean_text(match.group("start")),
            "end": clean_text(match.group("end")),
            "section": clean_text(match.group("section")),
            "visual": extract_field(body, "visual"),
            "audio": extract_field(body, "audio"),
            "text_on_screen": extract_field(body, "text_on_screen"),
            "fx": extract_field(body, "fx"),
            "editing_notes": extract_field(body, "editing_notes"),
            "style_text": extract_field(body, "style_text"),
            "tone_audio": extract_field(body, "tone_audio"),
            "warnings": [],
        }

        scene["warnings"] = validate_scene(scene)
        scenes.append(scene)

    return scenes


def validate_scene(scene: dict[str, Any]) -> list[str]:
    warnings = []

    required_fields = {
        "start": "No tiene tiempo de inicio.",
        "end": "No tiene tiempo de fin.",
        "visual": "No tiene campo Visual.",
        "audio": "No tiene campo Audio.",
        "text_on_screen": "No tiene Texto en pantalla.",
    }

    for field, message in required_fields.items():
        if not scene.get(field):
            warnings.append(message)

    return warnings


def parse_script(script_text: str) -> dict[str, Any]:
    title = extract_title(script_text)
    metadata = extract_metadata(script_text)
    scenes = parse_bracket_scene_blocks(script_text)

    return {
        "project_title": title,
        "metadata": metadata,
        "scenes": scenes,
        "scene_count": len(scenes),
    }
