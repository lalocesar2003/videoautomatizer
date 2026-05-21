# CURRENT_TASK.md

## Tarea actual

Implementar scoring de videos.

## Objetivo

Leer `data/pexels_results.json` y generar `data/scored_results.json` agregando un puntaje a cada sugerencia de video.

## Reglas de scoring

- +40 si el video es vertical.
- +25 si dura entre 4 y 20 segundos.
- +20 si es HD o superior.
- +10 si tiene thumbnail.
- +10 si coincide con la intención visual.
- -30 si es horizontal.
- -40 si dura demasiado.
- -50 si tiene logos, marcas o texto visible.

## Reglas de implementación

- No descargar videos.
- No implementar frontend.
- No llamar a Pexels.
- No modificar el parser.
- No rehacer el clasificador.
- No agregar dependencias nuevas.
- Mantener el scoring simple y transparente.
- El proyecto debe funcionar primero en terminal.

## Archivos permitidos para modificar

- scoring/video_scorer.py
- main.py
- data/scored_results.json
- tests/test_video_scorer.py

## No tocar

- parser/script_parser.py
- tests/test_parser.py
- ai/visual_classifier.py
- ai/ollama_provider.py
- tests/test_classifier.py
- providers/pexels_provider.py
- tests/test_pexels_provider.py
- script.md

## Criterio de éxito

Ejecutar:

python3 main.py score

Debe leer:

data/pexels_results.json

Y generar:

data/scored_results.json

con la misma estructura base de escenas, pero cada sugerencia debe incluir:

- score
- orientation
- score_breakdown
- requires_manual_review

La salida en terminal debe mostrar algo como:

Escena 1 → 5 sugerencias puntuadas
Mejor score: 95

## Nota

En esta fase, `semantic_match` y `has_logo_or_text` pueden quedar como valores preparados/manuales. No implementar visión artificial todavía.
