# CURRENT_TASK.md

## Tarea actual

Issue #24 — Preparar clips recortados según duración del guion.

Branch sugerida:

```bash
feature/24-prepare-clips
```

## Objetivo

Tomar los assets disponibles para cada escena y generar versiones preparadas con la duración exacta definida por el guion.

Esta fase debe producir clips listos para que la siguiente fase pueda renderizar `exports/preview_video.mp4` sin tener que decidir duraciones.

## Contexto importante

- El issue #21 genera `data/timeline.json` con el orden y duración de cada escena.
- El issue #22 detecta escenas faltantes en `data/missing_scenes.json`.
- El issue #23 genera placeholders en `exports/placeholders/`.
- El issue #24 no renderiza el video final.
- El issue #24 no descarga assets.
- El issue #24 no modifica clips originales.

## Entradas

Archivo principal:

```txt
data/timeline.json
```

Carpeta de clips descargados o copiados:

```txt
exports/clips/
```

Carpeta de placeholders disponible como respaldo:

```txt
exports/placeholders/
```

## Salida

Carpeta de clips preparados:

```txt
exports/prepared_clips/
```

Ejemplo:

```txt
exports/prepared_clips/scene_01_ready.mp4
exports/prepared_clips/scene_02_ready.mp4
exports/prepared_clips/scene_03_ready.mp4
```

Manifest recomendado:

```txt
exports/prepared_clips/prepared_manifest.json
```

## Estructura esperada del manifest

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "generated_at": "2026-05-26T00:00:00Z",
  "prepared_clips": [
    {
      "scene": 1,
      "status": "ready",
      "source_path": "exports/clips/scene_01_clip_01.mp4",
      "output_path": "exports/prepared_clips/scene_01_ready.mp4",
      "duration_seconds": 3,
      "source_duration_seconds": 10.2,
      "strategy": "trim"
    }
  ],
  "warnings": [],
  "summary": {
    "scene_count": 5,
    "prepared_count": 5,
    "warning_count": 0,
    "total_duration_seconds": 45
  }
}
```

## Reglas principales

Para cada escena de `data/timeline.json`:

1. Leer `duration_seconds`.
2. Ubicar el asset fuente.
3. Generar un archivo preparado en `exports/prepared_clips/`.
4. Nombrar el archivo de forma determinística:

```txt
scene_XX_ready.mp4
```

## Fuentes permitidas

La fuente puede venir de:

1. `clip_path` del timeline, si existe y apunta a un archivo real.
2. Placeholder correspondiente en `exports/placeholders/scene_XX_placeholder.mp4`, si la escena no tiene clip real.

No se debe buscar en Pexels ni descargar nada en esta fase.

## Reglas de duración

Si `source_duration > scene_duration`:

- recortar desde el inicio hasta `scene_duration`.
- estrategia: `trim`.

Si `source_duration == scene_duration` o la diferencia es mínima:

- generar/copiar una versión preparada.
- estrategia: `copy` o `normalize`.

Si `source_duration < scene_duration`:

- para MVP, no hacer loop automático.
- marcar warning claro.
- si existe placeholder para esa escena, se permite usarlo como respaldo.
- si no existe placeholder, marcar la escena como `needs_manual_review`.

Estrategias posibles:

```txt
trim
copy
placeholder
manual_review
```

Estrategias fuera de alcance por ahora:

```txt
loop
freeze_last_frame
```

## Dependencia externa

Se permite usar `ffmpeg` y `ffprobe` mediante `subprocess`.

Reglas:

- No agregar dependencias Python nuevas.
- Si falta `ffmpeg` o `ffprobe`, fallar con mensaje claro.
- Mantener compatibilidad con Python 3.12.

## Comando esperado

Agregar comando:

```bash
python3 main.py prepare
```

Salida esperada en terminal:

```txt
✅ Clips preparados
Carpeta: exports/prepared_clips
Preparados: 5
Warnings: 0
Duración total: 45s
```

Si hay clips cortos:

```txt
⚠️ Escena 2: clip más corto que la duración objetivo. Requiere revisión manual.
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `main.py`
- `preparation/__init__.py`
- `preparation/clip_preparer.py`
- `tests/test_clip_preparer.py`
- `README.md`
- `exports/prepared_clips/`
- `exports/prepared_clips/prepared_manifest.json`

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
- `timeline/timeline_generator.py`
- `missing/missing_scene_detector.py`
- `placeholders/placeholder_generator.py`
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`
- `data/selected_assets.json`
- `data/resolved_assets.json`
- `data/timeline.json`
- `data/missing_scenes.json`

## Criterios de aceptación

- `python3 main.py prepare` genera `exports/prepared_clips/`.
- Crea un archivo `scene_XX_ready.mp4` por cada escena que pueda resolverse con clip real o placeholder.
- Cada clip preparado dura lo mismo que `duration_seconds` de su escena.
- No modifica los clips originales en `exports/clips/`.
- No modifica placeholders originales en `exports/placeholders/`.
- Genera `exports/prepared_clips/prepared_manifest.json`.
- Reporta warnings para clips demasiado cortos.
- No descarga videos.
- No llama a Pexels.
- No llama a Ollama/Gemini/OpenAI.
- No renderiza `exports/preview_video.mp4`.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_clip_preparer.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Renderizar video preliminar final.
- Unir clips en un solo `.mp4`.
- Agregar audio, música, voz o subtítulos.
- Descargar clips.
- Buscar nuevos assets.
- Hacer loop automático.
- Congelar último frame automáticamente.
- Crear UI nueva.
