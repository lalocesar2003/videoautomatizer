import json
from typing import Any

from ai.provider_registry import Provider, get_provider


ASSET_TYPES = {
    "self_recorded",
    "screen_recording",
    "stock",
    "mixed",
}

VISUAL_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "visual_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene": {"type": "integer"},
                    "asset_type": {
                        "type": "string",
                        "enum": sorted(ASSET_TYPES),
                    },
                    "needs_pexels": {"type": "boolean"},
                    "primary_action": {"type": "string"},
                    "visual_intent": {"type": "string"},
                    "search_query_en": {"type": "string"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "scene",
                    "asset_type",
                    "needs_pexels",
                    "primary_action",
                    "visual_intent",
                    "search_query_en",
                    "confidence",
                    "reason",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["visual_plan"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """
Eres un director visual experto en videos cortos para TikTok, Reels, Shorts y LinkedIn.

Clasifica cada escena según el recurso visual principal que necesita.

Tipos permitidos:

- self_recorded: el creador aparece en cámara, habla, señala, sostiene un celular,
  mira a cámara o hace un llamado a la acción.
- screen_recording: se graba pantalla, dashboard, Excel, WhatsApp, interfaz,
  cursor, modal, botón, software, demo o app.
- stock: se necesita solo un clip externo de stock.
- mixed: combina grabación propia o pantalla con apoyo de stock.

Reglas obligatorias:
- self_recorded y screen_recording siempre tienen needs_pexels false.
- stock y mixed siempre tienen needs_pexels true.
- Si needs_pexels es false, search_query_en debe ser "".
- Si needs_pexels es true, search_query_en debe estar en inglés, ser corto,
  visual y concreto.
- No inventes elementos ajenos a la escena.
- Devuelve solo JSON válido siguiendo el schema.
""".strip()


def build_classifier_payload(parsed_script: dict[str, Any]) -> dict[str, Any]:
    scenes = parsed_script.get("scenes", [])

    return {
        "project_title": parsed_script.get("project_title", "Proyecto sin título"),
        "metadata": parsed_script.get("metadata", {}),
        "scenes": [
            {
                "scene": scene.get("scene"),
                "start": scene.get("start"),
                "end": scene.get("end"),
                "section": scene.get("section"),
                "visual": scene.get("visual"),
                "text_on_screen": scene.get("text_on_screen"),
                "audio": scene.get("audio"),
                "fx": scene.get("fx"),
                "editing_notes": scene.get("editing_notes"),
            }
            for scene in scenes
        ],
    }


def build_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    user_prompt = f"""
Clasifica estas escenas y responde solo JSON.

Schema obligatorio:
{json.dumps(VISUAL_PLAN_SCHEMA, ensure_ascii=False)}

Escenas:
{json.dumps(payload, ensure_ascii=False)}
""".strip()

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def normalize_item(
    item: dict[str, Any],
    scene: dict[str, Any] | None = None,
) -> dict[str, Any]:
    asset_type = infer_asset_type(scene or {}, clean_string(item.get("asset_type")))

    if asset_type not in ASSET_TYPES:
        raise ValueError(f"asset_type inválido: {asset_type}")

    needs_pexels = asset_type in {"stock", "mixed"}
    search_query = clean_string(item.get("search_query_en"))

    if not needs_pexels:
        search_query = ""

    if needs_pexels and not search_query:
        search_query = build_fallback_search_query(scene or {}, item)

    return {
        "scene": int(item.get("scene")),
        "asset_type": asset_type,
        "needs_pexels": needs_pexels,
        "primary_action": clean_string(item.get("primary_action"))
        or build_fallback_primary_action(scene or {}, asset_type),
        "visual_intent": clean_string(item.get("visual_intent"))
        or build_fallback_visual_intent(scene or {}, asset_type),
        "search_query_en": search_query,
        "confidence": clamp_confidence(item.get("confidence")),
        "reason": clean_string(item.get("reason")),
    }


def normalize_visual_plan(
    plan: list[dict[str, Any]],
    scenes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    scene_by_number = {
        scene.get("scene"): scene
        for scene in scenes or []
    }

    return [
        normalize_item(item, scene_by_number.get(item.get("scene")))
        for item in plan
    ]


def infer_asset_type(scene: dict[str, Any], model_asset_type: str) -> str:
    text = scene_text(scene)

    has_self_recording = any(
        keyword in text
        for keyword in [
            "frente a la cámara",
            "vuelves a salir",
            "sales tú",
            "creador",
            "postura de confianza",
            "señalas hacia abajo",
        ]
    )
    has_screen_recording = any(
        keyword in text
        for keyword in [
            "grabando la pantalla",
            "excel",
            "interfaz",
            "dashboard",
            "modal",
            "cursor",
            "botón",
            "next.js",
            "tarjetas",
            "historial",
        ]
    )
    has_stock = any(
        keyword in text
        for keyword in [
            "stock",
            "b-roll",
            "broll",
        ]
    )

    if has_self_recording and (has_stock or has_screen_recording):
        return "mixed"

    if has_screen_recording:
        return "screen_recording"

    if has_self_recording:
        return "self_recorded"

    if has_stock:
        return "stock"

    return model_asset_type


def build_fallback_search_query(
    scene: dict[str, Any],
    item: dict[str, Any],
) -> str:
    text = f"{scene_text(scene)} {clean_string(item.get('primary_action')).lower()} {clean_string(item.get('visual_intent')).lower()}"

    if "whatsapp" in text or "celular" in text or "phone" in text:
        return "person using smartphone"

    if "excel" in text or "spreadsheet" in text:
        return "spreadsheet on laptop"

    if "cliente" in text or "cobrar" in text or "pago" in text:
        return "business payment meeting"

    if "oficina" in text or "empresa" in text or "negocio" in text:
        return "business office people"

    return "business people working"


def build_fallback_primary_action(scene: dict[str, Any], asset_type: str) -> str:
    visual = clean_string(scene.get("visual"))

    if visual:
        return visual

    if asset_type == "self_recorded":
        return "Grabar al creador en cámara."

    if asset_type == "screen_recording":
        return "Grabar la pantalla indicada en la escena."

    if asset_type == "mixed":
        return "Combinar grabación propia con apoyo visual externo."

    return "Buscar un clip de stock acorde a la escena."


def build_fallback_visual_intent(scene: dict[str, Any], asset_type: str) -> str:
    text_on_screen = clean_string(scene.get("text_on_screen"))

    if text_on_screen:
        return text_on_screen

    if asset_type == "screen_recording":
        return "Mostrar evidencia visual del sistema o herramienta."

    if asset_type == "self_recorded":
        return "Transmitir confianza y dirección al espectador."

    if asset_type == "mixed":
        return "Reforzar la idea con una combinación de cámara y apoyo visual."

    return "Representar visualmente la idea de la escena."


def scene_text(scene: dict[str, Any]) -> str:
    return " ".join(
        [
            clean_string(scene.get("section")),
            clean_string(scene.get("visual")),
            clean_string(scene.get("text_on_screen")),
            clean_string(scene.get("audio")),
        ]
    ).lower()


def validate_scene_count(visual_plan: list[dict[str, Any]], scene_count: int) -> None:
    if len(visual_plan) != scene_count:
        raise ValueError(
            f"El proveedor devolvió {len(visual_plan)} clasificaciones, "
            f"pero scenes.json tiene {scene_count} escenas."
        )


def clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5

    return max(0.0, min(confidence, 1.0))


def classify_visual_scenes(
    parsed_script: dict[str, Any],
    provider: Provider | None = None,
) -> dict[str, Any]:
    if provider is None:
        provider = get_provider()

    payload = build_classifier_payload(parsed_script)
    messages = build_messages(payload)
    response = provider(messages, VISUAL_PLAN_SCHEMA)

    raw_plan = response.get("visual_plan")

    if not isinstance(raw_plan, list):
        raise ValueError("La respuesta del proveedor no contiene visual_plan como lista.")

    visual_plan = normalize_visual_plan(raw_plan, payload["scenes"])
    validate_scene_count(visual_plan, len(payload["scenes"]))

    return {
        "project_title": payload["project_title"],
        "format": payload["metadata"].get("format") or "Vertical",
        "visual_plan": visual_plan,
    }
