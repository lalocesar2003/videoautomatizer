# CURRENT_TASK.md

## Tarea actual

Implementar clasificador visual con Ollama.

## Objetivo

Leer `data/scenes.json` y generar `data/visual_plan.json` clasificando cada escena en:

- self_recorded
- screen_recording
- stock
- mixed

## Reglas

- self_recorded → needs_pexels = false
- screen_recording → needs_pexels = false
- stock → needs_pexels = true
- mixed → needs_pexels = true

## Archivos permitidos para modificar

- ai/visual_classifier.py
- ai/ollama_provider.py
- main.py
- data/visual_plan.json
- tests/test_classifier.py

## No tocar

- parser/script_parser.py
- providers/pexels_provider.py
- scoring/video_scorer.py
- script.md

## Criterio de éxito

Ejecutar:

python3 main.py classify

Debe generar:

data/visual_plan.json

con una clasificación por cada escena del `scenes.json`.

También debe mostrar en terminal algo como:

Escena 1 → mixed → needs_pexels true
Escena 2 → mixed o screen_recording → needs_pexels según corresponda
Escena 3 → screen_recording → needs_pexels false
Escena 4 → screen_recording → needs_pexels false
Escena 5 → self_recorded → needs_pexels false
