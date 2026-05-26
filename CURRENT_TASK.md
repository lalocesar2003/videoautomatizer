# CURRENT_TASK.md

## Tarea actual

Issue #22 — Detectar escenas faltantes o pendientes.

Branch sugerida:

```bash
feature/22-missing-scenes
```

## Objetivo

Crear un reporte claro de escenas que **no están listas para el render automático**.

Esta fase audita `data/timeline.json` y genera `data/missing_scenes.json` con razones accionables.

No resuelve escenas. No crea placeholders. No descarga clips. Solo reporta qué falta o qué necesita revisión.

## Contexto importante

- El issue #20 genera `data/resolved_assets.json`.
- El issue #21 genera `data/timeline.json`.
- `timeline.json` ya contiene tiempos, duración, `status`, `resolution_type`, `clip_path`, `primary_action`, `asset_type` y mensajes.
- Este issue debe consumir `timeline.json` como fuente principal.
- El siguiente issue (#23) usará este reporte para generar placeholders.

## Entrada obligatoria

```txt
data/timeline.json
```

## Salida

```txt
data/missing_scenes.json
```

## Estructura esperada

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "generated_at": "2026-05-26T00:00:00Z",
  "missing_scenes": [
    {
      "scene": 3,
      "start": "0:08",
      "end": "0:20",
      "duration_seconds": 12,
      "asset_type": "screen_recording",
      "resolution_type": "missing_asset",
      "status": "needs_screen_recording",
      "severity": "blocking",
      "reason": "La escena requiere una grabación de pantalla y no tiene asset listo.",
      "primary_action": "Grabar interfaz de SusyCafe.",
      "suggested_action": "Grabar pantalla o asignar un video local desde el panel."
    }
  ],
  "summary": {
    "missing_count": 3,
    "blocking_count": 3,
    "warning_count": 0
  }
}
```

## Estados que deben reportarse como faltantes

Reportar como `severity = "blocking"`:

```txt
needs_self_recording
needs_screen_recording
needs_manual_review
needs_fallback_search
missing_asset
```

## Assets rotos o inexistentes

También reportar como `severity = "blocking"` si una escena tiene:

```txt
status = ready
```

o:

```txt
status = fallback_stock
```

pero:

- `clip_path` está vacío o `null`;
- el archivo indicado en `clip_path` no existe localmente.

En estos casos el reporte debe indicar que el asset fue marcado como listo, pero el archivo no está disponible para render.

## Placeholders

Si una escena tiene:

```txt
status = placeholder
```

no debe reportarse como faltante en esta fase.

Motivo: el placeholder es una resolución temporal válida. El issue #23 se encargará de crear el archivo placeholder real.

## Reglas de reason y suggested_action

El reporte debe explicar claramente el problema:

### `needs_self_recording`

```txt
reason = "La escena requiere grabación del creador y no tiene asset local listo."
suggested_action = "Grabar al creador o asignar un video local desde el panel."
```

### `needs_screen_recording`

```txt
reason = "La escena requiere una grabación de pantalla y no tiene asset listo."
suggested_action = "Grabar pantalla o asignar un video local desde el panel."
```

### `needs_fallback_search`

```txt
reason = "La escena necesita stock de relleno, pero todavía no tiene sugerencias disponibles."
suggested_action = "Ejecutar una búsqueda fallback en una fase posterior o marcar placeholder."
```

### `missing_asset`

```txt
reason = "La escena no tiene asset seleccionado ni resolución lista para render."
suggested_action = "Seleccionar Pexels, asignar video local, usar fallback stock o marcar placeholder."
```

### `needs_manual_review`

```txt
reason = "La escena requiere revisión manual antes del render."
suggested_action = "Revisar la escena y elegir una resolución válida."
```

### Asset roto o inexistente

```txt
reason = "La escena fue marcada como lista, pero el archivo indicado en clip_path no existe."
suggested_action = "Ejecutar export, corregir clip_path o volver a seleccionar el asset."
```

## Comando esperado

Agregar comando:

```bash
python3 main.py missing
```

Debe generar:

```txt
data/missing_scenes.json
```

Salida esperada en terminal:

```txt
✅ Reporte de escenas faltantes generado
Archivo generado: data/missing_scenes.json
Faltantes: 3
Bloqueantes: 3
Warnings: 0
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `main.py`
- `missing/__init__.py`
- `missing/missing_scene_detector.py`
- `tests/test_missing_scene_detector.py`
- `README.md`
- `data/missing_scenes.json`

## No tocar

- `parser/script_parser.py`
- `tests/test_parser.py`
- `ai/visual_classifier.py`
- `ai/ollama_provider.py`
- `ai/provider_registry.py`
- `ai/script_generator.py`
- `providers/pexels_provider.py`
- `scoring/video_scorer.py`
- `downloaders/zip_downloader.py`
- `panel/streamlit_panel.py`
- `selection/asset_selector.py`
- `resolution/asset_resolver.py`
- `tests/test_asset_resolver.py`
- `timeline/timeline_generator.py`
- `tests/test_timeline_generator.py`
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`
- `data/selected_assets.json`
- `data/resolved_assets.json`
- `data/timeline.json`

## Criterios de aceptación

- `python3 main.py missing` genera `data/missing_scenes.json`.
- Detecta escenas con `needs_self_recording`.
- Detecta escenas con `needs_screen_recording`.
- Detecta escenas con `needs_manual_review`.
- Detecta escenas con `needs_fallback_search`.
- Detecta escenas con `missing_asset`.
- Detecta escenas listas con `clip_path` vacío o inexistente.
- No reporta placeholders como faltantes.
- Cada escena reportada incluye `reason` claro.
- Cada escena reportada incluye `suggested_action` concreta.
- No descarga clips.
- No copia clips.
- No crea placeholders.
- No modifica `timeline.json`.
- No renderiza video.
- No llama a Pexels.
- No llama a Ollama/Gemini/OpenAI.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_missing_scene_detector.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Crear clips placeholder.
- Reparar assets rotos.
- Ejecutar export automáticamente.
- Buscar fallback stock.
- Modificar selección de assets.
- Crear timeline.
- Renderizar video preliminar.
- Agregar UI nueva.
