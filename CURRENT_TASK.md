# CURRENT_TASK.md

## Tarea actual

Issue #25 — Renderizar video preliminar sin audio final.

Branch sugerida:

```bash
feature/25-preview-render
```

## Objetivo

Leer el timeline y los clips preparados para generar un primer video preliminar en orden, sin audio final, sin subtítulos finales y sin edición fina.

Esta fase debe producir:

```txt
exports/preview_video.mp4
```

El video preliminar debe servir como base visual para revisar ritmo, orden de escenas y cobertura de assets antes de agregar voz, música, subtítulos o edición final.

## Contexto importante

- El issue #21 genera `data/timeline.json`.
- El issue #23 genera placeholders en `exports/placeholders/`.
- El issue #24 genera clips preparados en `exports/prepared_clips/` con duración exacta por escena.
- Esta fase une clips ya preparados o placeholders.
- Esta fase no decide assets nuevos.
- Esta fase no recorta clips originales.
- Esta fase no genera audio final.

## Entradas

Archivo principal:

```txt
data/timeline.json
```

Carpeta principal de clips listos:

```txt
exports/prepared_clips/
```

Carpeta de respaldo:

```txt
exports/placeholders/
```

Manifest opcional de preparación:

```txt
exports/prepared_clips/prepared_manifest.json
```

## Salida

Archivo final de esta fase:

```txt
exports/preview_video.mp4
```

Manifest recomendado:

```txt
exports/preview_manifest.json
```

Archivo temporal permitido:

```txt
exports/concat_list.txt
```

## Estructura esperada del manifest

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "generated_at": "2026-05-27T00:00:00Z",
  "output_path": "exports/preview_video.mp4",
  "timeline": [
    {
      "scene": 1,
      "source_path": "exports/prepared_clips/scene_01_ready.mp4",
      "duration_seconds": 3,
      "status": "ready",
      "strategy": "prepared_clip"
    },
    {
      "scene": 3,
      "source_path": "exports/placeholders/scene_03_placeholder.mp4",
      "duration_seconds": 12,
      "status": "placeholder",
      "strategy": "placeholder_fallback"
    }
  ],
  "warnings": [],
  "summary": {
    "scene_count": 5,
    "rendered_scene_count": 5,
    "warning_count": 0,
    "total_duration_seconds": 45
  }
}
```

## Reglas de selección de fuente

Para cada escena de `data/timeline.json`, en orden:

1. Usar `exports/prepared_clips/scene_XX_ready.mp4` si existe.
2. Si no existe, usar `exports/placeholders/scene_XX_placeholder.mp4` si existe.
3. Si no existe ninguno, fallar con mensaje claro indicando la escena faltante.

No buscar en `exports/clips/` directamente en esta fase. Los clips reales deben pasar primero por `python3 main.py prepare`.

## Reglas de render

- Unir clips en el orden del guion.
- Respetar `duration_seconds` de cada escena.
- Usar placeholders cuando falte un clip preparado.
- No agregar audio final.
- No agregar subtítulos finales.
- No agregar música final.
- No llamar a Pexels.
- No llamar a Ollama/Gemini/OpenAI.
- No descargar videos.
- No modificar `data/timeline.json`.
- No modificar clips preparados.
- No modificar placeholders.

## Regla técnica importante

Para evitar errores de concatenación, el render puede normalizar los clips a un formato uniforme antes de unirlos.

Formato recomendado para MVP:

```txt
1080x1920
24 fps
H.264
pix_fmt yuv420p
sin audio
```

Se permite crear archivos temporales dentro de:

```txt
exports/render_tmp/
```

Estos archivos temporales no deben versionarse.

## Dependencia externa

Se permite usar `ffmpeg` y `ffprobe` mediante `subprocess`.

Reglas:

- No agregar dependencias Python nuevas.
- Si falta `ffmpeg` o `ffprobe`, fallar con mensaje claro.
- Mantener compatibilidad con Python 3.12.

## Comando esperado

Agregar comando:

```bash
python3 main.py render
```

Debe generar:

```txt
exports/preview_video.mp4
exports/preview_manifest.json
```

Salida esperada en terminal:

```txt
✅ Video preliminar generado
Archivo: exports/preview_video.mp4
Escenas renderizadas: 5
Duración total: 45s
Warnings: 0
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `main.py`
- `rendering/__init__.py`
- `rendering/preview_renderer.py`
- `tests/test_preview_renderer.py`
- `README.md`
- `exports/preview_video.mp4`
- `exports/preview_manifest.json`
- `exports/concat_list.txt`
- `exports/render_tmp/`

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
- `preparation/clip_preparer.py`
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

- `python3 main.py render` genera `exports/preview_video.mp4`.
- El video respeta el orden de escenas de `data/timeline.json`.
- Usa `exports/prepared_clips/scene_XX_ready.mp4` cuando existe.
- Usa `exports/placeholders/scene_XX_placeholder.mp4` cuando falta el preparado.
- Respeta `duration_seconds` por escena.
- No falla si hay placeholders.
- Genera `exports/preview_manifest.json`.
- No agrega audio final.
- No agrega subtítulos finales.
- No llama a Pexels.
- No llama a IA.
- No descarga videos.
- El resultado queda listo para agregar audio después.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_preview_renderer.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Agregar voz en off.
- Agregar música.
- Agregar subtítulos.
- Agregar overlays finales.
- Transiciones avanzadas.
- Exportar versiones para múltiples plataformas.
- Editor notes.
- UI nueva.
