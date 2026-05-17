# PROJECT_PLAN.md

## Objetivo del proyecto

Crear un asistente visual para videos cortos que sugiera B-roll a partir de guiones técnicos.

## Fase 1: Parser

Entrada:

- script.md

Salida:

- data/scenes.json

Debe extraer:

- título
- tiempo
- sección
- visual
- audio
- texto en pantalla
- fx
- notas de edición

## Fase 2: Clasificador visual

Entrada:

- data/scenes.json

Salida:

- data/visual_plan.json

Debe clasificar:

- self_recorded
- screen_recording
- stock
- mixed

Debe generar:

- needs_pexels
- primary_action
- visual_intent
- search_query_en
- confidence
- reason

## Fase 3: Pexels Search

Entrada:

- data/visual_plan.json

Salida:

- data/pexels_results.json

Solo busca escenas con:

- needs_pexels = true

## Fase 4: Scoring

Puntaje:

- +40 si es vertical
- +25 si dura entre 4 y 20 segundos
- +20 si es HD o superior
- +10 si tiene thumbnail
- +10 si coincide con intención visual
- -30 si es horizontal
- -40 si dura demasiado
- -50 si tiene logos, marcas o texto visible

## Fase 5: Panel

Mostrar:

- escenas
- tipo visual
- query
- thumbnails
- preview_url
- score
- botón seleccionar
- botón rebuscar
