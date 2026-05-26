# CURRENT_TASK.md

## Tarea actual

Issue #21 — Generar `timeline.json` usando assets resueltos.

Branch sugerida:

```bash
feature/21-timeline-generator
```

## Objetivo

Generar `data/timeline.json` ordenando las escenas según los tiempos del guion y vinculando cada escena con su asset resuelto o con su estado pendiente.

Esta fase convierte:

```txt
scenes.json + visual_plan.json + resolved_assets.json
↓
timeline.json
```

El timeline será la base para las siguientes fases:

```txt
missing_scenes.json
placeholders
prepared_clips
preview_video.mp4
```

## Contexto importante

- El parser ya genera `data/scenes.json`.
- El clasificador ya genera `data/visual_plan.json`.
- El issue #20 ya genera `data/resolved_assets.json`.
- `resolved_assets.json` es la fuente de verdad para saber si una escena usa Pexels, asset local, fallback stock, placeholder o queda pendiente.
- Esta fase no debe volver a decidir assets desde `selected_assets.json`.

## Entradas obligatorias

```txt
data/scenes.json
data/visual_plan.json
data/resolved_assets.json
```

## Salida

```txt
data/timeline.json
```

## Estructura esperada

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "generated_at": "2026-05-26T00:00:00Z",
  "timeline": [
    {
      "scene": 1,
      "start": "0:00",
      "end": "0:03",
      "start_seconds": 0,
      "end_seconds": 3,
      "duration_seconds": 3,
      "section": "EL GANCHO",
      "asset_type": "mixed",
      "resolution_type": "pexels",
      "status": "ready",
      "clip_path": "exports/clips/scene_01_clip_01.mp4",
      "primary_action": "...",
      "visual_intent": "...",
      "text_on_screen": "...",
      "audio": "...",
      "message": "Clip Pexels seleccionado."
    },
    {
      "scene": 3,
      "start": "0:08",
      "end": "0:20",
      "start_seconds": 8,
      "end_seconds": 20,
      "duration_seconds": 12,
      "section": "LA SOLUCIÓN Y EL ORDEN",
      "asset_type": "screen_recording",
      "resolution_type": "missing_asset",
      "status": "needs_screen_recording",
      "clip_path": null,
      "primary_action": "Grabar pantalla del dashboard.",
      "visual_intent": "...",
      "text_on_screen": "...",
      "audio": "...",
      "message": "Grabar pantalla o interfaz."
    }
  ],
  "summary": {
    "scene_count": 5,
    "ready_count": 2,
    "pending_count": 3,
    "total_duration_seconds": 45
  }
}
```

## Reglas de duración

- Calcular `start_seconds` desde `scene.start`.
- Calcular `end_seconds` desde `scene.end`.
- Calcular `duration_seconds = end_seconds - start_seconds`.
- Si la duración es menor o igual a 0, fallar con mensaje claro.
- Soportar al menos formato `M:SS` y `H:MM:SS`.

Ejemplos:

```txt
0:00 → 0
0:03 → 3
1:05 → 65
1:02:03 → 3723
```

## Reglas de orden

- Ordenar las escenas por `start_seconds`.
- Si dos escenas tienen el mismo `start_seconds`, ordenar por número de escena.
- No reordenar por asset ni por status.

## Reglas de vínculo con assets

### 1. Escena `ready` con `resolution_type = "pexels"`

Debe generar:

```txt
clip_path = exports/clips/scene_XX_clip_01.mp4
status = ready
```

### 2. Escena `ready` con `resolution_type = "local"`

Debe generar `clip_path` usando la extensión del `local_path` original:

```txt
local_assets/dashboard.mov
↓
exports/clips/scene_03_clip_01.mov
```

Si no hay extensión, usar `.mp4` como fallback.

### 3. Escena con `resolution_type = "fallback_stock"`

Si tiene `selected_clip`, debe generar:

```txt
clip_path = exports/clips/scene_XX_clip_01.mp4
status = fallback_stock
```

Si no tiene `selected_clip`, debe mantener:

```txt
clip_path = null
status = needs_fallback_search
```

### 4. Escena con `resolution_type = "placeholder"`

Debe marcar:

```txt
status = placeholder
clip_path = null
```

No crear placeholder de video todavía.

### 5. Escena pendiente o sin asset

Para estos estados:

```txt
needs_self_recording
needs_screen_recording
needs_manual_review
needs_fallback_search
missing_asset
```

Debe generar:

```txt
clip_path = null
```

## Estados permitidos

```txt
ready
fallback_stock
placeholder
needs_self_recording
needs_screen_recording
needs_fallback_search
missing_asset
needs_manual_review
```

## Comando esperado

Agregar comando:

```bash
python3 main.py timeline
```

Debe generar:

```txt
data/timeline.json
```

Salida esperada en terminal:

```txt
✅ Timeline generado
Archivo generado: data/timeline.json
Escenas: 5
Duración total: 45s
Ready: 2
Pendientes: 3
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `main.py`
- `timeline/__init__.py`
- `timeline/timeline_generator.py`
- `tests/test_timeline_generator.py`
- `README.md`
- `data/timeline.json`

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
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`
- `data/selected_assets.json`
- `data/resolved_assets.json`

## Criterios de aceptación

- `python3 main.py timeline` genera `data/timeline.json`.
- El timeline tiene una entrada por cada escena de `data/scenes.json`.
- Las escenas están ordenadas por tiempo de inicio.
- Calcula `start_seconds`, `end_seconds` y `duration_seconds` correctamente.
- Calcula `total_duration_seconds`.
- Vincula escenas `ready` con `clip_path` esperado en `exports/clips/`.
- Preserva estados pendientes desde `resolved_assets.json`.
- Marca escenas sin asset con `clip_path = null`.
- No descarga clips.
- No copia clips.
- No crea placeholders.
- No recorta clips.
- No renderiza video.
- No llama a Pexels.
- No llama a Ollama/Gemini/OpenAI.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_timeline_generator.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Detectar escenas faltantes en `missing_scenes.json`.
- Crear clips placeholder.
- Preparar/recortar clips.
- Verificar con FFmpeg si el clip existe o cuánto dura realmente.
- Renderizar video preliminar.
- Agregar UI nueva.
