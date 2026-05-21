# CURRENT_TASK.md

## Tarea actual

Implementar panel simple de resultados.

## Objetivo

Leer `data/scored_results.json` y generar una vista simple para revisar las sugerencias puntuadas de B-roll.

El panel debe permitir inspeccionar:

- escena
- tipo visual
- intención visual
- query
- thumbnails
- preview_url
- page_url
- score
- score_breakdown

## Alcance

Esta fase es un panel simple de revisión, no un producto final.

Debe funcionar primero en terminal y puede generar un HTML estático local para visualizar mejor los thumbnails.

## Reglas de implementación

- No descargar videos.
- No montar videos.
- No implementar login.
- No implementar pagos.
- No implementar base de datos.
- No llamar a Pexels.
- No llamar a Ollama.
- No modificar parser, clasificador, búsqueda Pexels ni scoring.
- No agregar dependencias nuevas.
- Mantener HTML/CSS simple si se genera un archivo HTML.

## Archivos permitidos para modificar

- panel/results_panel.py
- main.py
- output/results_panel.html
- tests/test_results_panel.py

## No tocar

- parser/script_parser.py
- tests/test_parser.py
- ai/visual_classifier.py
- ai/ollama_provider.py
- tests/test_classifier.py
- providers/pexels_provider.py
- tests/test_pexels_provider.py
- scoring/video_scorer.py
- tests/test_video_scorer.py
- script.md

## Criterio de éxito

Ejecutar:

python3 main.py panel

Debe leer:

data/scored_results.json

Y generar:

output/results_panel.html

La terminal debe mostrar algo como:

Panel generado: output/results_panel.html
Escenas: 1
Sugerencias: 5

## Requisitos del HTML

El HTML debe mostrar por sugerencia:

- escena
- tipo visual
- intención visual
- query
- thumbnail
- score
- orientation
- duration
- resolution
- author_name
- link a page_url
- link a preview_url

## Nota

Los botones `seleccionar` y `rebuscar` pueden quedar como botones visuales deshabilitados o placeholders.
No implementar interacción real todavía.
