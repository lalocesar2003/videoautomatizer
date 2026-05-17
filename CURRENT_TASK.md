# CURRENT_TASK.md

## Tarea actual

Corregir y estabilizar el parser de guiones.

## Objetivo

El parser debe leer `script.md` con formato:

[0:00 - 0:03] EL GANCHO
• Visual: ...
• Texto en pantalla: ...
• Audio: ...

Y generar `data/scenes.json`.

## Archivos permitidos para modificar

- parser/script_parser.py
- main.py
- tests/test_parser.py

## No tocar

- ai/visual_classifier.py
- providers/pexels_provider.py
- scoring/video_scorer.py

## Criterio de éxito

Ejecutar:

python3 main.py parse

Debe generar:

data/scenes.json

con todas las escenas detectadas.
