# CURRENT_TASK.md

## Tarea actual

Implementar Fase 5A: panel interactivo local con Streamlit para revisar y seleccionar clips.

## Objetivo

Crear una interfaz local en Python que lea `data/scored_results.json`, muestre los clips sugeridos por escena, permita seleccionar manualmente los clips más interesantes y guarde la selección en `data/selected_assets.json`.

Esta fase NO debe descargar clips ni generar ZIP.

## Contexto del proyecto

El proyecto es un sistema de B-roll automático para videos cortos.

Flujo actual:

script.md
→ parser
→ data/scenes.json
→ clasificador visual
→ data/visual_plan.json
→ búsqueda Pexels
→ data/pexels_results.json
→ scoring
→ data/scored_results.json
→ panel Streamlit
→ selección manual
→ data/selected_assets.json

## Entrada esperada

Archivo:

`data/scored_results.json`

Cada sugerencia puede tener:

- provider
- provider_id
- page_url
- thumbnail_url
- preview_url
- duration
- width
- height
- orientation
- author_name
- author_url
- score
- score_breakdown

## Salida esperada

Crear o actualizar:

`data/selected_assets.json`

Estructura esperada:

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "selected_assets": [
    {
      "scene": 1,
      "asset_type": "mixed",
      "visual_intent": "Persona frustrada usando celular por problemas de cobranza.",
      "query": "frustrated businessman using phone messaging app",
      "selected_clip": {
        "provider": "pexels",
        "provider_id": "123456",
        "page_url": "https://...",
        "preview_url": "https://...",
        "thumbnail_url": "https://...",
        "duration": 8,
        "width": 1080,
        "height": 1920,
        "orientation": "vertical",
        "author_name": "Autor",
        "score": 95,
        "score_breakdown": {}
      }
    }
  ]
}
```

## Requisitos funcionales

- Crear panel local con Streamlit.
- Leer data/scored_results.json.
- Mostrar escenas y clips sugeridos.
- Permitir seleccionar clips con checkbox.
- Guardar selección en data/selected_assets.json.
- No descargar clips.
- No generar ZIP.
- No llamar a Pexels.
- No llamar a Ollama.

## Dependencias permitidas

- streamlit

## Archivos permitidos para modificar o crear

- app.py
- panel/streamlit_panel.py
- selection/asset_selector.py
- data/selected_assets.json
- requirements.txt
- README.md
- tests/test_asset_selector.py

## No tocar

- parser/script_parser.py
- tests/test_parser.py
- ai/visual_classifier.py
- ai/ollama_provider.py
- providers/pexels_provider.py
- scoring/video_scorer.py
- script.md

## Comando esperado

streamlit run app.py
