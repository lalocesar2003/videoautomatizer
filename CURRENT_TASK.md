# CURRENT_TASK.md

## Tarea actual

Issue #26 — Panel de control del pipeline en Streamlit.

Branch sugerida:

```bash
feature/26-streamlit-pipeline-control
```

## Objetivo

Agregar al panel Streamlit una sección de control que permita ejecutar manualmente las fases principales del sistema desde botones individuales, sin tener que volver a la terminal para cada comando.

Esta fase debe convertir la UI en un tablero de operación del pipeline, manteniendo visibilidad y control sobre cada paso.

## Contexto importante

El backend del MVP ya tiene comandos funcionales en `main.py`:

```txt
parse
classify
search
score
export
resolve
timeline
missing
placeholders
prepare
render
```

El panel Streamlit actual ya permite revisar clips y guardar `data/selected_assets.json`.

Esta tarea NO debe implementar todavía el botón único de “generar todo”. Ese será el issue siguiente.

## Objetivo de producto

El usuario debe poder abrir:

```bash
streamlit run app.py
```

Y ver:

1. Estado de cada fase.
2. Botón para ejecutar cada fase individual.
3. Resultado o error claro después de ejecutar.
4. Acceso visual al preview final si `exports/preview_video.mp4` existe.

## Entradas

Archivos existentes del pipeline:

```txt
script.md
data/scenes.json
data/visual_plan.json
data/pexels_results.json
data/scored_results.json
data/selected_assets.json
data/resolved_assets.json
data/timeline.json
data/missing_scenes.json
exports/placeholders/placeholder_manifest.json
exports/prepared_clips/prepared_manifest.json
exports/preview_video.mp4
```

## Salidas esperadas

La UI debe poder generar, según el botón presionado:

```txt
data/scenes.json
data/visual_plan.json
data/pexels_results.json
data/scored_results.json
exports/clips/
exports/selected_broll.zip
data/resolved_assets.json
data/timeline.json
data/missing_scenes.json
exports/placeholders/
exports/prepared_clips/
exports/preview_video.mp4
```

## Botones esperados

Agregar botones individuales para:

```txt
Parsear guion
Clasificar escenas
Buscar en Pexels
Puntuar clips
Exportar seleccionados
Resolver assets
Generar timeline
Detectar faltantes
Generar placeholders
Preparar clips
Renderizar preview
```

Cada botón debe ejecutar una sola fase.

## Estados esperados por fase

Cada fase debe mostrar si su output principal existe:

| Fase | Output principal |
|---|---|
| Parsear | `data/scenes.json` |
| Clasificar | `data/visual_plan.json` |
| Buscar | `data/pexels_results.json` |
| Puntuar | `data/scored_results.json` |
| Selección manual | `data/selected_assets.json` |
| Exportar | `exports/selected_broll.zip` |
| Resolver | `data/resolved_assets.json` |
| Timeline | `data/timeline.json` |
| Missing | `data/missing_scenes.json` |
| Placeholders | `exports/placeholders/placeholder_manifest.json` |
| Prepare | `exports/prepared_clips/prepared_manifest.json` |
| Render | `exports/preview_video.mp4` |

Estados visuales sugeridos:

```txt
✅ Listo
⚠️ Pendiente
❌ Error al ejecutar
```

## Reglas de ejecución

- Reutilizar las funciones existentes del backend.
- No duplicar la lógica de parse, classify, search, score, export, resolve, timeline, missing, placeholders, prepare ni render.
- Cada botón debe ejecutar solo una fase.
- Mostrar errores con `st.error(...)`.
- Mostrar éxito con `st.success(...)`.
- Si una fase necesita prerrequisitos y faltan archivos, mostrar error claro.
- No borrar `data/*.json`.
- No borrar archivos en `exports/`.
- No crear un botón que ejecute todo todavía.

## Reglas sobre operaciones lentas

Algunas fases pueden tardar o depender de servicios externos:

- `classify` necesita Ollama o proveedor IA configurado.
- `search` necesita `PEXELS_API_KEY`.
- `export` descarga o copia assets seleccionados.
- `placeholders`, `prepare` y `render` necesitan `ffmpeg` / `ffprobe`.

La UI debe dejar claro cuando una fase falla por falta de configuración o dependencia.

## Preview del resultado

Si existe:

```txt
exports/preview_video.mp4
```

El panel debe mostrarlo con `st.video(...)` o, como mínimo, mostrar la ruta del archivo generado.

## Integración con selección manual

La sección actual de selección manual debe mantenerse.

El flujo ideal dentro de la UI será:

```txt
1. Ejecutar parse/classify/search/score desde botones.
2. Revisar y seleccionar assets en el panel existente.
3. Guardar selected_assets.json.
4. Ejecutar export/resolve/timeline/missing/placeholders/prepare/render desde botones.
5. Ver preview_video.mp4.
```

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `app.py`
- `panel/streamlit_panel.py`
- `panel/pipeline_control.py`
- `tests/test_pipeline_control.py`
- `README.md`

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
- `selection/asset_selector.py`
- `resolution/asset_resolver.py`
- `timeline/timeline_generator.py`
- `missing/missing_scene_detector.py`
- `placeholders/placeholder_generator.py`
- `preparation/clip_preparer.py`
- `rendering/preview_renderer.py`
- `main.py`
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`
- `data/selected_assets.json`
- `data/resolved_assets.json`
- `data/timeline.json`
- `data/missing_scenes.json`
- `exports/preview_video.mp4`

## Criterios de aceptación

- `streamlit run app.py` abre el panel sin romper la selección manual existente.
- La UI muestra el estado de cada fase según sus archivos output.
- La UI tiene botones individuales para ejecutar fases del pipeline.
- Al ejecutar una fase exitosa, muestra mensaje de éxito.
- Al fallar una fase, muestra error claro.
- La selección manual actual sigue funcionando y genera `data/selected_assets.json`.
- Si existe `exports/preview_video.mp4`, se muestra en el panel o se muestra su ruta claramente.
- No se implementa botón único de flujo completo todavía.
- No se modifica lógica interna del backend.
- No se agregan dependencias nuevas.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_pipeline_control.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Botón único “Generar preview completo”.
- Ejecución automática de todo el pipeline.
- Generación de guion desde prompt en la UI.
- Selección automática por mejor score.
- Audio final.
- Música.
- Subtítulos.
- Transiciones avanzadas.
- Editor notes.
