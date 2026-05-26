# CURRENT_TASK.md

## Tarea actual

Issue #20 — Resolver escenas sin asset: local / stock fallback / placeholder / pendiente.

Branch sugerida:

```bash
feature/20-resolve-assets
```

## Objetivo

Generar `data/resolved_assets.json` con una resolución clara para **cada escena del guion** antes de construir el timeline.

Esta fase traduce lo que existe en `data/selected_assets.json` a un contrato más útil para las siguientes fases:

```txt
selected_assets.json
↓
resolved_assets.json
↓
timeline.json
```

`selected_assets.json` dice qué seleccionó el usuario. `resolved_assets.json` debe decir qué hará el sistema con cada escena.

## Contexto importante

- El parser ya está cerrado.
- El clasificador ya está cerrado.
- Pexels search ya está cerrado.
- Scoring ya está cerrado.
- El panel ya permite seleccionar máximo un asset por escena.
- El issue #19 ya permite assets locales con `selection_type = "local"` y `provider = "local"`.

Esta fase **no debe volver a resolver uploads locales desde cero**. Solo debe consumir lo que ya venga en `data/selected_assets.json`.

## Entradas obligatorias

```txt
data/scenes.json
data/visual_plan.json
data/selected_assets.json
```

## Entrada opcional

```txt
data/resolution_choices.json
```

Este archivo sirve para expresar decisiones manuales sin crear UI nueva todavía.

Ejemplo:

```json
{
  "resolutions": [
    {
      "scene": 3,
      "resolution_type": "placeholder",
      "message": "Usar placeholder hasta grabar pantalla del dashboard."
    },
    {
      "scene": 5,
      "resolution_type": "missing_asset",
      "message": "Pendiente de grabar al creador en cámara."
    },
    {
      "scene": 2,
      "resolution_type": "fallback_stock"
    }
  ]
}
```

Si el archivo no existe, el resolver debe aplicar defaults razonables.

## Entrada opcional para fallback stock

```txt
data/scored_results.json
```

Solo se puede leer para saber si ya existen sugerencias puntuadas para una escena.

Reglas:

- No llamar a Pexels automáticamente.
- No buscar clips nuevos.
- Si el usuario elige `fallback_stock` y ya existen sugerencias para esa escena, se puede usar la mejor sugerencia disponible.
- Si el usuario elige `fallback_stock` y no hay sugerencias, marcar `status = "needs_fallback_search"`.

## Salida

```txt
data/resolved_assets.json
```

Estructura esperada:

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "generated_at": "2026-05-26T00:00:00Z",
  "resolved_assets": [
    {
      "scene": 1,
      "asset_type": "mixed",
      "resolution_type": "pexels",
      "status": "ready",
      "message": "Clip Pexels seleccionado.",
      "selected_clip": {
        "provider": "pexels",
        "provider_id": "123456",
        "preview_url": "https://..."
      }
    },
    {
      "scene": 3,
      "asset_type": "screen_recording",
      "resolution_type": "missing_asset",
      "status": "needs_screen_recording",
      "message": "Grabar pantalla del dashboard.",
      "selected_clip": null
    },
    {
      "scene": 4,
      "asset_type": "screen_recording",
      "resolution_type": "placeholder",
      "status": "placeholder",
      "message": "Usar placeholder hasta tener grabación real.",
      "selected_clip": null
    }
  ]
}
```

## Resolution types permitidos

```txt
pexels
local
fallback_stock
placeholder
missing_asset
```

## Status permitidos

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

## Reglas de resolución

### 1. Escena con `selection_type = "pexels"`

Debe generar:

```txt
resolution_type = pexels
status = ready
selected_clip = clip seleccionado
```

### 2. Escena con `selection_type = "local"`

Debe generar:

```txt
resolution_type = local
status = ready
selected_clip = asset local
```

Debe preservar:

```txt
selected_clip.provider = local
selected_clip.local_path
```

### 3. Escena con `selection_type = "manual_task"`

Si no hay override en `resolution_choices.json`, debe convertirse en:

- `asset_type = self_recorded` → `status = needs_self_recording`
- `asset_type = screen_recording` → `status = needs_screen_recording`
- otro tipo → `status = needs_manual_review`

En estos casos:

```txt
resolution_type = missing_asset
selected_clip = null
```

### 4. Escena sin selección en `selected_assets.json`

Si no hay override en `resolution_choices.json`, resolver según `asset_type`:

- `self_recorded` → `needs_self_recording`
- `screen_recording` → `needs_screen_recording`
- `stock` → `missing_asset`
- `mixed` → `missing_asset`

### 5. Override `placeholder`

Si `resolution_choices.json` indica:

```json
{ "scene": 3, "resolution_type": "placeholder" }
```

Debe generar:

```txt
resolution_type = placeholder
status = placeholder
selected_clip = null
```

No debe generar video placeholder todavía. Eso corresponde a un issue posterior.

### 6. Override `fallback_stock`

Si `resolution_choices.json` indica:

```json
{ "scene": 3, "resolution_type": "fallback_stock" }
```

Reglas:

- Si existe una sugerencia en `data/scored_results.json` para esa escena, usar la mejor sugerencia.
- Si no existe sugerencia, generar:

```txt
resolution_type = fallback_stock
status = needs_fallback_search
selected_clip = null
```

No llamar a Pexels en esta fase.

### 7. Override `missing_asset`

Debe dejar la escena como pendiente con un mensaje claro.

Ejemplo:

```txt
resolution_type = missing_asset
status = needs_screen_recording
message = Grabar pantalla del dashboard.
```

## Regla de selección

Una escena debe terminar con **máximo una resolución**.

No usar checkboxes múltiples si se toca UI en el futuro. Si se necesita UI, usar:

```txt
radio button
selectbox
```

Pero esta tarea debe funcionar primero por terminal.

## Comando esperado

Agregar comando:

```bash
python3 main.py resolve
```

Debe generar:

```txt
data/resolved_assets.json
```

Salida esperada en terminal:

```txt
✅ Resolución de assets terminada
Archivo generado: data/resolved_assets.json
Escenas resueltas: 5
Ready: 2
Pendientes: 3
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `main.py`
- `resolution/__init__.py`
- `resolution/asset_resolver.py`
- `tests/test_asset_resolver.py`
- `README.md`
- `data/resolved_assets.json`
- `data/resolution_choices.json`

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
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`
- `data/selected_assets.json`

## Criterios de aceptación

- `python3 main.py resolve` genera `data/resolved_assets.json`.
- El archivo tiene una entrada por cada escena de `data/scenes.json`.
- Las escenas con Pexels seleccionado quedan `resolution_type = "pexels"` y `status = "ready"`.
- Las escenas con asset local quedan `resolution_type = "local"` y `status = "ready"`.
- Las escenas `self_recorded` sin asset local quedan `needs_self_recording`.
- Las escenas `screen_recording` sin asset local quedan `needs_screen_recording`.
- Las escenas con `manual_task` se convierten a estado pendiente correcto.
- `placeholder` queda registrado, pero no genera video.
- `fallback_stock` usa sugerencia existente si ya hay una disponible.
- `fallback_stock` sin sugerencias queda `needs_fallback_search`.
- No llama a Pexels.
- No llama a Ollama/Gemini/OpenAI.
- No descarga clips.
- No copia clips.
- No genera timeline.
- No renderiza video.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_asset_resolver.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Subir assets locales desde el panel.
- Descargar clips.
- Copiar clips a `exports/clips/`.
- Crear placeholders de video.
- Crear `missing_scenes.json`.
- Crear `timeline.json`.
- Recortar clips.
- Renderizar video preliminar.
- Agregar frontend nuevo.
