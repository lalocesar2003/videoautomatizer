# CURRENT_TASK.md

## Tarea actual

Issue #23 — Generar clips placeholder para escenas faltantes.

Branch sugerida:

```bash
feature/23-video-placeholders
```

## Objetivo

Crear clips placeholder para que el video preliminar no se rompa cuando falte una escena o cuando un asset marcado como listo todavía no exista localmente.

Esta fase consume el reporte de escenas faltantes y genera videos placeholder reales en disco, con la misma duración que cada escena.

## Contexto importante

- El issue #21 genera `data/timeline.json`.
- El issue #22 genera `data/missing_scenes.json`.
- `missing_scenes.json` puede incluir:
  - escenas pendientes de grabación;
  - escenas sin asset;
  - escenas `ready` cuyo `clip_path` todavía no existe localmente.
- Esta fase debe crear un placeholder por cada entrada de `missing_scenes.json`.
- El render preliminar posterior podrá usar estos placeholders si no existe un clip real.

## Dependencia externa

Para generar clips de video reales se permite usar `ffmpeg` mediante `subprocess`.

Reglas:

- No agregar dependencias Python nuevas.
- Si `ffmpeg` no está instalado, fallar con mensaje claro.
- No descargar nada.
- No llamar a Pexels.
- No llamar a Ollama/Gemini/OpenAI.

## Entradas obligatorias

```txt
data/missing_scenes.json
data/timeline.json
```

## Salidas

Carpeta de clips placeholder:

```txt
exports/placeholders/
```

Archivos esperados:

```txt
exports/placeholders/scene_01_placeholder.mp4
exports/placeholders/scene_02_placeholder.mp4
exports/placeholders/scene_03_placeholder.mp4
```

Manifest opcional pero recomendado para consumo posterior:

```txt
exports/placeholders/placeholder_manifest.json
```

## Estructura esperada del manifest

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "generated_at": "2026-05-26T00:00:00Z",
  "placeholders": [
    {
      "scene": 3,
      "path": "exports/placeholders/scene_03_placeholder.mp4",
      "duration_seconds": 12,
      "asset_type": "screen_recording",
      "status": "needs_screen_recording",
      "reason": "La escena requiere una grabación de pantalla y no tiene asset listo.",
      "primary_action": "Grabar interfaz de SusyCafe."
    }
  ],
  "summary": {
    "placeholder_count": 1,
    "total_duration_seconds": 12
  }
}
```

## Contenido visual del placeholder

El clip debe ser simple y legible.

Debe mostrar texto equivalente a:

```txt
ESCENA 3 FALTANTE
Tipo: screen_recording
Estado: needs_screen_recording
Acción: Grabar dashboard de SusyCafe
Duración: 12 segundos
```

Para MVP, el diseño puede ser:

- fondo oscuro;
- texto blanco;
- resolución vertical `1080x1920`;
- sin audio;
- formato `.mp4`;
- duración exacta según `duration_seconds`.

## Reglas de duración

- Cada placeholder debe durar exactamente `duration_seconds` de la escena.
- Si `duration_seconds` falta, es cero o es inválido, fallar con mensaje claro.
- No calcular duración desde tiempos en esta fase si ya viene en `missing_scenes.json`.
- `timeline.json` se puede usar para validar o complementar datos si falta contexto.

## Reglas de generación

- Crear un placeholder por cada entrada de `missing_scenes.json`.
- Usar nombres determinísticos:

```txt
scene_XX_placeholder.mp4
```

- Si el archivo ya existe, se puede sobrescribir.
- No modificar `data/timeline.json`.
- No modificar `data/missing_scenes.json`.
- No generar video final.
- No recortar clips reales.
- No tocar assets reales.

## Comando esperado

Agregar comando:

```bash
python3 main.py placeholders
```

Debe generar:

```txt
exports/placeholders/
exports/placeholders/placeholder_manifest.json
```

Salida esperada en terminal:

```txt
✅ Placeholders generados
Carpeta: exports/placeholders
Placeholders: 3
Duración total: 37s
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `main.py`
- `placeholders/__init__.py`
- `placeholders/placeholder_generator.py`
- `tests/test_placeholder_generator.py`
- `README.md`
- `exports/placeholders/`
- `exports/placeholders/placeholder_manifest.json`

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
- `missing/missing_scene_detector.py`
- `tests/test_missing_scene_detector.py`
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

- `python3 main.py placeholders` genera un clip por cada escena en `data/missing_scenes.json`.
- Cada clip queda en `exports/placeholders/`.
- Cada clip usa nombre `scene_XX_placeholder.mp4`.
- Cada clip dura lo mismo que `duration_seconds`.
- Cada placeholder muestra escena, tipo, estado, acción y duración.
- Genera `exports/placeholders/placeholder_manifest.json`.
- El manifest incluye una entrada por placeholder.
- No modifica `timeline.json`.
- No modifica `missing_scenes.json`.
- No descarga clips.
- No llama a APIs externas.
- Falla con mensaje claro si falta `ffmpeg`.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_placeholder_generator.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Renderizar `exports/preview_video.mp4`.
- Recortar clips reales.
- Preparar clips en `exports/prepared_clips/`.
- Actualizar `timeline.json` con paths de placeholder.
- Generar audio, música, subtítulos o voz.
- Crear UI nueva.
