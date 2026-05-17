import json
import os
from typing import Any

import requests


VISUAL_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "visual_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene": {
                        "type": "integer"
                    },
                    "asset_type": {
                        "type": "string",
                        "enum": [
                            "self_recorded",
                            "screen_recording",
                            "stock",
                            "mixed"
                        ]
                    },
                    "needs_pexels": {
                        "type": "boolean"
                    },
                    "primary_action": {
                        "type": "string"
                    },
                    "visual_intent": {
                        "type": "string"
                    },
                    "search_query_en": {
                        "type": "string"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "reason": {
                        "type": "string"
                    }
                },
                "required": [
                    "scene",
                    "asset_type",
                    "needs_pexels",
                    "primary_action",
                    "visual_intent",
                    "search_query_en",
                    "confidence",
                    "reason"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["visual_plan"],
    "additionalProperties": False
}


SYSTEM_PROMPT = """
Eres un director visual experto en videos cortos para TikTok, Reels, Shorts y LinkedIn.

Tu tarea es clasificar escenas de un guion técnico según el tipo de recurso visual que necesitan.

Tipos permitidos:

1. self_recorded
Cuando la escena pide que el creador aparezca en cámara, hable, señale, sostenga un celular, haga gestos, mire a cámara o cierre con CTA.

2. screen_recording
Cuando la escena requiere grabar pantalla, dashboard, software, Excel, WhatsApp, interfaz, modal, cursor, botón, demo de producto o una app.

3. stock
Cuando la escena necesita un video externo de stock: personas, oficinas, negocios, construcción, finanzas, clientes, estrés, reuniones, tecnología, etc.

4. mixed
Cuando la escena combina grabación propia o grabación de pantalla con apoyo opcional de stock.

Reglas obligatorias:
- Si asset_type es stock o mixed, needs_pexels debe ser true.
- Si asset_type es self_recorded o screen_recording, needs_pexels debe ser false.
- Si needs_pexels es false, search_query_en debe ser una cadena vacía.
- Si needs_pexels es true, search_query_en debe estar en inglés.
- search_query_en debe ser corta, visual y concreta.
- No uses frases poéticas para search_query_en.
- No inventes elementos ajenos a la escena.
- Devuelve solo JSON válido siguiendo exactamente el schema.
"""


def normalize_visual_plan(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []

    for item in plan:
        asset_type = item.get("asset_type")

        if asset_type in ["stock", "mixed"]:
            item["needs_pexels"] = True

            if not item.get("search_query_en"):
                item["search_query_en"] = "business office people working"

        if asset_type in ["self_recorded", "screen_recording"]:
            item["needs_pexels"] = False
            item["search_query_en"] = ""

        try:
            item["confidence"] = max(0, min(float(item.get("confidence", 0)), 1))
        except (TypeError, ValueError):
            item["confidence"] = 0.5

        normalized.append(item)

    return normalized


def call_ollama_classifier(payload: dict[str, Any]) -> dict[str, Any]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    url = f"{base_url}/api/chat"

    user_prompt = f"""
Clasifica estas escenas.

IMPORTANTE:
Responde únicamente JSON válido.
No agregues explicación fuera del JSON.

JSON Schema obligatorio:
{json.dumps(VISUAL_PLAN_SCHEMA, ensure_ascii=False)}

Escenas:
{json.dumps(payload, ensure_ascii=False)}
"""

    response = requests.post(
        url,
        json={
            "model": model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "format": VISUAL_PLAN_SCHEMA,
            "options": {
                "temperature": 0
            }
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()
    content = data.get("message", {}).get("content", "")

    if not content:
        raise ValueError("Ollama no devolvió contenido.")

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"Ollama devolvió JSON inválido:\n{content}") from error


def classify_visual_scenes(parsed_script: dict[str, Any]) -> dict[str, Any]:
    project_title = parsed_script.get("project_title", "Proyecto sin título")
    metadata = parsed_script.get("metadata", {})
    scenes = parsed_script.get("scenes", [])

    payload = {
        "project_title": project_title,
        "metadata": metadata,
        "scenes": [
            {
                "scene": scene.get("scene"),
                "start": scene.get("start"),
                "end": scene.get("end"),
                "section": scene.get("section"),
                "visual": scene.get("visual"),
                "audio": scene.get("audio"),
                "text_on_screen": scene.get("text_on_screen"),
                "fx": scene.get("fx"),
                "editing_notes": scene.get("editing_notes"),
            }
            for scene in scenes
        ],
    }

    data = call_ollama_classifier(payload)

    visual_plan = data.get("visual_plan", [])

    if not isinstance(visual_plan, list):
        raise ValueError("La respuesta de Ollama no contiene visual_plan como lista.")

    visual_plan = normalize_visual_plan(visual_plan)

    return {
        "project_title": project_title,
        "format": metadata.get("format", "Vertical"),
        "visual_plan": visual_plan,
    }