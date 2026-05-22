# CURRENT_TASK.md

## Tarea actual

Issue #5 — Hacer configurable el proveedor de IA vía `.env`.

## Objetivo

Desacoplar `ai/visual_classifier.py` de Ollama. El proveedor de IA se
elige en tiempo de ejecución leyendo `AI_PROVIDER` de `.env`. Añadir un
nuevo proveedor debe ser cuestión de añadir un archivo y registrarlo,
sin tocar el clasificador ni el pipeline.

Este issue **solo arma la abstracción**. Ollama queda como único
proveedor funcional. Gemini y OpenAI son fuera de alcance (issues
separados).

## Contexto del proyecto

Flujo actual:

script.md
→ parser
→ data/scenes.json
→ clasificador visual (Ollama hardcodeado — eso cambia aquí)
→ data/visual_plan.json
→ búsqueda Pexels
→ data/pexels_results.json
→ scoring
→ data/scored_results.json
→ panel Streamlit
→ selección manual
→ data/selected_assets.json

## Requisitos funcionales

- `get_provider()` lee `AI_PROVIDER` de `.env` y devuelve el proveedor.
- Cada proveedor valida sus variables requeridas al construirse
  (fail fast, mensaje claro, nunca loggear la key).
- Error claro si `AI_PROVIDER` no está definido, es desconocido, o
  apunta a un proveedor aún no implementado (gemini / openai).
- `ai/visual_classifier.py` deja de importar Ollama directamente y
  usa el registro de proveedores.
- `.env.example` lista todas las keys soportadas con placeholders.
- `DECISIONS.md` Decisión #4 reescrita con el contrato nuevo.
- Tests con `monkeypatch` del entorno, sin llamadas reales a APIs.

## Archivos permitidos para modificar o crear

- ai/visual_classifier.py
- ai/ollama_provider.py
- ai/provider_registry.py (nuevo)
- ai/__init__.py
- .env.example
- DECISIONS.md
- tests/test_provider_registry.py (nuevo)
- CURRENT_TASK.md
- CHANGELOG.md

## No tocar

- parser/script_parser.py
- providers/pexels_provider.py
- scoring/video_scorer.py
- panel/streamlit_panel.py
- panel/results_panel.py
- selection/asset_selector.py
- app.py
- main.py
- script.md
- requirements.txt
- data/*.json

## Fuera de alcance

- Implementar el proveedor Gemini (issue separado, depende de este).
- Implementar el proveedor OpenAI.
- Scoring multimodal de thumbnails.
- Cambiar el comportamiento del clasificador (mismos prompts, mismos
  outputs).

## Comando esperado

python3 main.py classify

Debe seguir funcionando exactamente igual con `AI_PROVIDER=ollama`.
