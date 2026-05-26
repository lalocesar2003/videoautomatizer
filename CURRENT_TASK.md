# CURRENT_TASK.md

## Tarea actual

Issue #19 — Permitir asignar assets locales a escenas.

Branch sugerida:

```bash
feature/19-local-assets
```

## Objetivo

Permitir que el usuario use videos propios cuando Pexels no tenga una buena opción o cuando la escena requiera grabación propia.

Ejemplos:

- `self_recorded` → `local_assets/scene_05_yo_hablando.mp4`
- `screen_recording` → `local_assets/scene_03_dashboard_demo.mp4`
- `mixed` o `stock` → usar asset local si el usuario prefiere no usar Pexels.

Esta fase extiende el panel Streamlit y el exportador para que `data/selected_assets.json` soporte assets locales sin romper el flujo existente de Pexels.

## Entradas

Archivos existentes:

```txt
data/scenes.json
data/visual_plan.json
data/scored_results.json
```

Entrada del usuario desde el panel:

```txt
archivos de video locales seleccionados o subidos por escena
```

## Salidas

Archivo principal:

```txt
data/selected_assets.json
```

Carpeta local para guardar/copiar assets subidos desde el panel:

```txt
local_assets/
```

El comando de export debe seguir generando:

```txt
exports/clips/
exports/selected_broll.zip
```

## Estructura esperada para asset local

```json
{
  "scene": 3,
  "asset_type": "screen_recording",
  "selection_type": "local",
  "visual_intent": "Mostrar el dashboard funcionando.",
  "query": "",
  "selected_clip": {
    "provider": "local",
    "local_path": "local_assets/scene_03_dashboard_demo.mp4",
    "original_filename": "dashboard_demo.mp4"
  }
}
```

## Relación con tareas manuales

El issue #17 ya permite guardar escenas como:

```json
{
  "selection_type": "manual_task"
}
```

Este issue debe permitir que una escena manual pase a:

```json
{
  "selection_type": "local",
  "selected_clip": {
    "provider": "local",
    "local_path": "local_assets/..."
  }
}
```

Reglas:

- `self_recorded` puede quedar como tarea manual o resolverse con asset local.
- `screen_recording` puede quedar como tarea manual o resolverse con asset local.
- `stock` y `mixed` pueden usar Pexels o asset local.
- Cada escena debe mantener máximo un asset seleccionado.

## Reglas obligatorias

- El panel debe permitir registrar un asset local por escena.
- `data/selected_assets.json` debe soportar `selection_type = "local"`.
- `selected_clip.provider` debe ser `"local"` para assets locales.
- El sistema debe diferenciar assets de Pexels y assets locales.
- El exportador debe copiar assets locales desde `local_path` hacia `exports/clips/`.
- El exportador debe seguir descargando assets Pexels usando `preview_url`.
- El ZIP debe incluir clips de Pexels y clips locales seleccionados.
- El ZIP debe incluir una copia de `selected_assets.json`.
- No descargar assets locales.
- No llamar a Pexels Search.
- No llamar a Ollama/Gemini/OpenAI.
- No modificar parser, clasificador, búsqueda Pexels ni scoring.
- No recortar clips todavía.
- No generar timeline todavía.
- No renderizar video todavía.
- No agregar dependencias nuevas salvo justificación clara.

## Nombres esperados en exports/clips

Para mantener consistencia con el export actual:

```txt
scene_01_clip_01.mp4
scene_02_clip_01.mp4
scene_03_clip_01.mp4
```

Si el asset local original es `.mov`, `.webm` o `.m4v`, se permite conservar la extensión:

```txt
scene_03_clip_01.mov
```

## Validaciones mínimas

El sistema debe fallar o avisar con mensaje claro si:

- el archivo local no existe;
- `local_path` está vacío;
- el asset local no tiene una extensión de video soportada;
- no se puede copiar el asset local a `exports/clips/`;
- `selected_assets.json` no contiene ningún asset exportable.

Extensiones soportadas para esta fase:

```txt
.mp4
.mov
.webm
.m4v
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `.gitignore`
- `panel/streamlit_panel.py`
- `selection/asset_selector.py`
- `downloaders/zip_downloader.py`
- `main.py`
- `tests/test_asset_selector.py`
- `tests/test_zip_downloader.py`
- `README.md`
- `local_assets/.gitkeep`

Archivos generados localmente, no necesariamente versionados:

- `local_assets/*.mp4`
- `local_assets/*.mov`
- `local_assets/*.webm`
- `local_assets/*.m4v`
- `data/selected_assets.json`
- `exports/clips/`
- `exports/selected_broll.zip`

## No tocar

- `parser/script_parser.py`
- `tests/test_parser.py`
- `ai/visual_classifier.py`
- `ai/ollama_provider.py`
- `ai/provider_registry.py`
- `ai/script_generator.py`
- `providers/pexels_provider.py`
- `scoring/video_scorer.py`
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`

## Criterios de aceptación

Panel:

- `streamlit run app.py` abre el panel.
- Cada escena permite máximo un asset seleccionado.
- Cada escena permite elegir `Ninguno por ahora`.
- Las escenas manuales permiten elegir `Tarea manual / pendiente`.
- Las escenas permiten registrar un asset local.
- Guardar selección genera `data/selected_assets.json`.
- El JSON diferencia `selection_type = "pexels"`, `selection_type = "manual_task"` y `selection_type = "local"`.
- Una escena manual puede pasar de `manual_task` a `local`.

Export:

- `python3 main.py export` sigue funcionando.
- Los clips Pexels se descargan con `preview_url`.
- Los clips locales se copian desde `local_path`.
- Los clips locales quedan en `exports/clips/`.
- `exports/selected_broll.zip` incluye clips locales y Pexels seleccionados.
- `exports/selected_broll.zip` incluye `selected_assets.json`.
- No intenta descargar clips locales.
- No exporta escenas marcadas como `manual_task`.

Tests:

```bash
.venv/bin/python -m pytest tests/test_asset_selector.py tests/test_zip_downloader.py
```

Debe pasar.

## Fuera de alcance

- Recortar clips según duración del guion.
- Crear `resolved_assets.json`.
- Crear `timeline.json`.
- Detectar escenas faltantes.
- Generar placeholders.
- Renderizar video preliminar.
- Analizar duración real del archivo con FFmpeg.
- Subir archivos a la nube.
