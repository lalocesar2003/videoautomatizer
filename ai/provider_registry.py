"""
Registro de proveedores de IA.

Contrato del proveedor:
    Provider = Callable[[list[dict[str, str]], dict[str, Any]], dict[str, Any]]

El proveedor recibe la lista de mensajes (formato chat: role + content)
y un schema JSON, y devuelve un dict ya parseado que cumple ese schema.

El proveedor activo se elige en tiempo de ejecución leyendo la variable
de entorno AI_PROVIDER. Cada proveedor valida sus propias variables al
construirse y falla rápido con un mensaje claro si faltan.
"""

import os
from typing import Any, Callable


Provider = Callable[[list[dict[str, str]], dict[str, Any]], dict[str, Any]]
ProviderFactory = Callable[[], Provider]


def _build_ollama_provider() -> Provider:
    from ai.ollama_provider import call_ollama_json

    return call_ollama_json


def _build_unimplemented_provider(name: str, required_key: str) -> ProviderFactory:
    def factory() -> Provider:
        raise NotImplementedError(
            f"Proveedor '{name}' aún no implementado. "
            f"Cuando se implemente, requerirá {required_key} en .env. "
            f"Por ahora usa AI_PROVIDER=ollama."
        )

    return factory


PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "ollama": _build_ollama_provider,
    "gemini": _build_unimplemented_provider("gemini", "GEMINI_API_KEY"),
    "openai": _build_unimplemented_provider("openai", "OPENAI_API_KEY"),
}


def get_provider() -> Provider:
    name = os.getenv("AI_PROVIDER", "").strip().lower()

    if not name:
        raise RuntimeError(
            "Falta AI_PROVIDER en .env. "
            f"Proveedores disponibles: {', '.join(sorted(PROVIDER_FACTORIES))}."
        )

    factory = PROVIDER_FACTORIES.get(name)

    if factory is None:
        raise RuntimeError(
            f"Proveedor desconocido: '{name}'. "
            f"Disponibles: {', '.join(sorted(PROVIDER_FACTORIES))}."
        )

    return factory()
