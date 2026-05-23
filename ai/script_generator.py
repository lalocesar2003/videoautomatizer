"""
Generador de script.md a partir de un brief corto.

El usuario describe su idea en brief.md (tema, duración, tono, audiencia,
CTA). Este módulo le pide al proveedor de IA configurado que escriba un
guion completo respetando el formato que parse_script() entiende.

El output se valida con parse_script() antes de guardarse. Si el formato
está mal, se reintenta con feedback del error al modelo.
"""

import json
import re
from typing import Any

from ai.provider_registry import Provider, get_provider
from parser.script_parser import parse_script


MAX_RETRIES = 2


class GenerationError(ValueError):
    """Lanzada cuando el proveedor no logra producir un guion válido."""

    def __init__(self, message: str, last_attempt: str = ""):
        super().__init__(message)
        self.last_attempt = last_attempt

BRIEF_FIELDS = {
    "topic": r"Tema",
    "platform": r"Plataforma",
    "target_duration": r"Duraci[oó]n\s+objetivo",
    "tone": r"Tono",
    "audience": r"Audiencia",
    "cta": r"CTA",
    "product": r"Producto",
    "notes": r"Notas",
}


SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "script_markdown": {
            "type": "string",
            "minLength": 100,
        }
    },
    "required": ["script_markdown"],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """
Eres un copywriter experto en videos cortos para TikTok, Reels y Shorts.

Tu tarea es escribir un guion técnico completo a partir de un brief.

Formato OBLIGATORIO del guion (lo va a parsear un programa, debe ser exacto):

# Guion para TikTok: "Título del video"

[0:00 - 0:03] EL GANCHO
• Visual: descripción concreta de qué se ve.
• Texto en pantalla: caption corto en mayúsculas si aplica.
• Audio: lo que se escucha (narración en off).

[0:03 - 0:08] EL PROBLEMA
• Visual: ...
• Texto en pantalla: ...
• Audio: ...

(continúa con tantas escenas como necesite el video)

Reglas estrictas:

- La primera línea del guion debe empezar con `# Guion para` seguido del título entre comillas.
- Cada escena empieza con `[M:SS - M:SS] NOMBRE DE SECCIÓN`.
- Cada escena tiene OBLIGATORIAMENTE las tres líneas: `• Visual:`, `• Texto en pantalla:`, `• Audio:`.
- Los timestamps son contiguos: la escena 2 empieza donde termina la 1, etc.
- La última escena termina en o cerca del tiempo objetivo del brief.
- Cada `• Visual:` describe acción visual concreta y filmable (no abstracta).
- El tono y el CTA reflejan el brief.
- Idioma: español neutro de Latinoamérica.
- NO uses emojis dentro de las líneas Visual/Audio (los textos en pantalla sí pueden tener uno o dos).
- NO inventes campos extra. Solo Visual, Texto en pantalla, Audio.

Devuelve solo JSON con un único campo `script_markdown` cuyo valor es
el guion completo como string.
""".strip()


FEW_SHOT_EXAMPLE = """
# Guion para TikTok: "El Fin del Excel para Cobrar"

[0:00 - 0:03] EL GANCHO
• Visual: Grabación tuya frente a la cámara con cara de frustración, sosteniendo tu celular, haciendo scroll rápido y mostrando un chat de WhatsApp borroso o imagen de stock.
• Texto en pantalla: DEJA DE ROGAR POR TU SALDO
• Audio: Si tienes una agencia o constructora, rogarle a tus clientes para que te paguen el saldo es el peor error que estás cometiendo.

[0:03 - 0:08] EL PROBLEMA
• Visual: B-Roll rápido grabando la pantalla con un Excel aburrido. Filtro blanco y negro rápido.
• Texto en pantalla: El Excel oculta tus deudas.
• Audio: Si todavía llevas el control en un Excel desordenado, se te van a pasar las fechas, vas a perder autoridad y tu negocio se desangra.

[0:08 - 0:20] LA SOLUCIÓN Y EL ORDEN
• Visual: Swoosh. Transición a la grabación de una interfaz en Next.js con dashboard oscuro. Zoom suave a las Tarjetas de Expediente mostrando montos.
• Texto en pantalla: Orden total: Quién, Cuánto y Cuándo
• Audio: Por eso diseñé este Centro de Comando. Olvídate de adivinar: aquí tienes un orden visual exacto de quién te debe, cuánto falta y la fecha límite para cobrarles.

[0:20 - 0:32] LA MAGIA Y LA DELEGACIÓN
• Visual: Acercamiento al botón del Rayo. Clic y aparece el modal de WhatsApp. Cursor señala el historial de cobros.
• Texto en pantalla: Cualquiera de tu equipo puede cobrar
• Audio: Con un solo botón, armas un mensaje formal por WhatsApp. Lo mejor: cualquiera de tu equipo puede enviarlo sin miedo a equivocarse.

[0:32 - 0:45] EL LLAMADO A LA ACCIÓN
• Visual: Vuelves a salir tú en cámara, con postura de confianza. Señalas hacia abajo.
• Texto en pantalla: Escribe SISTEMA al DM
• Audio: Este sistema es para proyectos High-Ticket. Busco a 5 empresas para implementarlo este mes. Si quieres dejar de perseguir clientes, mándame la palabra SISTEMA.
""".strip()


def clean(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def unescape_literal_newlines(text: str) -> str:
    """
    Algunos modelos pequeños (ej. llama3.2:3b) doble-escapan los saltos
    de línea en JSON: el resultado decodificado contiene los literales
    `\\n`, `\\t`, `\\r` como texto en vez de los caracteres reales.
    Esto los convierte de vuelta.
    """
    return (
        text
        .replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\r", "\n")
    )


def parse_brief(brief_text: str) -> dict[str, str]:
    """Extrae los campos del brief.md. Solo 'topic' es obligatorio."""
    brief: dict[str, str] = {}

    for key, label in BRIEF_FIELDS.items():
        pattern = rf"^\s*{label}\s*:\s*(.+?)\s*$"
        match = re.search(pattern, brief_text, re.IGNORECASE | re.MULTILINE)
        brief[key] = clean(match.group(1)) if match else ""

    if not brief["topic"]:
        raise ValueError(
            "El brief.md no tiene el campo 'Tema'. "
            "Mira brief.md.example para el formato esperado."
        )

    return brief


def build_messages(
    brief: dict[str, str],
    previous_attempt: str = "",
    previous_error: str = "",
) -> list[dict[str, str]]:
    user_prompt_parts = [
        "Genera un guion de TikTok a partir de este brief:",
        "",
        f"Tema: {brief['topic']}",
    ]

    optional_fields = [
        ("Plataforma", brief.get("platform")),
        ("Duración objetivo", brief.get("target_duration")),
        ("Tono", brief.get("tone")),
        ("Audiencia", brief.get("audience")),
        ("CTA", brief.get("cta")),
        ("Producto", brief.get("product")),
        ("Notas", brief.get("notes")),
    ]

    for label, value in optional_fields:
        if value:
            user_prompt_parts.append(f"{label}: {value}")

    user_prompt_parts += [
        "",
        "Ejemplo del formato exacto que debes producir:",
        "",
        FEW_SHOT_EXAMPLE,
        "",
        "Devuelve JSON con un único campo `script_markdown` cuyo valor sea "
        "el guion completo como string.",
    ]

    if previous_attempt:
        user_prompt_parts += [
            "",
            "ATENCIÓN: tu intento anterior falló la validación. "
            f"Error: {previous_error}",
            "",
            "Intento anterior:",
            previous_attempt,
            "",
            "Corrige los errores y respeta el formato exacto.",
        ]

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_prompt_parts)},
    ]


def validate_generated_script(script_markdown: str) -> None:
    parsed = parse_script(script_markdown)

    if parsed["scene_count"] < 1:
        raise ValueError("El guion no tiene ninguna escena reconocible.")

    if parsed["project_title"] == "Proyecto sin título":
        raise ValueError(
            "Falta el título. La primera línea debe ser "
            '`# Guion para TikTok: "Título del video"`.'
        )

    warnings: list[str] = []

    for scene in parsed["scenes"]:
        if scene["warnings"]:
            for warning in scene["warnings"]:
                warnings.append(f"Escena {scene['scene']}: {warning}")

    if warnings:
        raise ValueError(
            "Las escenas generadas tienen campos faltantes:\n- "
            + "\n- ".join(warnings)
        )


def generate_script(
    brief: dict[str, str],
    provider: Provider | None = None,
    max_retries: int = MAX_RETRIES,
) -> str:
    if provider is None:
        provider = get_provider()

    previous_attempt = ""
    previous_error = ""

    for attempt in range(max_retries + 1):
        messages = build_messages(brief, previous_attempt, previous_error)
        response = provider(messages, SCRIPT_SCHEMA)

        script_markdown = unescape_literal_newlines(
            clean(response.get("script_markdown"))
        )

        if not script_markdown:
            previous_attempt = json.dumps(response, ensure_ascii=False)
            previous_error = "La respuesta no incluye el campo script_markdown."

            if attempt == max_retries:
                raise GenerationError(
                    f"El proveedor no devolvió script_markdown tras "
                    f"{max_retries + 1} intentos.",
                    last_attempt=previous_attempt,
                )

            continue

        try:
            validate_generated_script(script_markdown)
        except ValueError as error:
            previous_attempt = script_markdown
            previous_error = str(error)

            if attempt == max_retries:
                raise GenerationError(
                    f"El proveedor no pudo generar un guion válido tras "
                    f"{max_retries + 1} intentos. Último error: {error}",
                    last_attempt=script_markdown,
                ) from error

            continue

        return script_markdown

    raise RuntimeError("Flujo inesperado en generate_script.")
