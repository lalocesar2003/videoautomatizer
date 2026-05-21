# CURRENT_TASK.md

## Tarea actual

Implementar búsqueda de videos en Pexels.

## Objetivo

Leer `data/visual_plan.json` y generar `data/pexels_results.json` buscando videos solo para escenas con:

- needs_pexels = true

## Reglas

- No buscar escenas con `needs_pexels = false`.
- Usar `search_query_en` como query.
- Si el formato del proyecto es vertical, usar orientación `portrait`.
- No descargar videos.
- No implementar scoring todavía.
- Guardar resultados normalizados y legibles.

## Archivos permitidos para modificar

- providers/pexels_provider.py
- main.py
- data/pexels_results.json
- tests/test_pexels_provider.py

## No tocar

- parser/script_parser.py
- tests/test_parser.py
- ai/visual_classifier.py
- ai/ollama_provider.py
- tests/test_classifier.py
- scoring/video_scorer.py
- script.md

## Criterio de éxito

Ejecutar:

python3 main.py search

Debe leer:

data/visual_plan.json

Y generar:

data/pexels_results.json

con resultados solo para escenas donde:

needs_pexels = true

La salida debe incluir:

- scene
- asset_type
- visual_intent
- query
- suggestions
- page_url
- preview_url
- thumbnail_url
- duration
- width
- height
- orientation
- author_name
- author_url
