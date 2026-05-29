# CURRENT_TASK.md

## Tarea actual

Issue #28 — Clarificar acciones finales de Preview y descarga.

Branch sugerida:

```bash
feature/28-preview-actions
```

## Objetivo

Corregir la confusión en la UI guiada alrededor de los botones finales:

```txt
Confirmar selección
Preview
Generar Video preliminar / Descargar
```

La experiencia actual permite que `Preview` guarde selección y genere el video al mismo tiempo, lo que no deja claro qué hizo el usuario ni cuánto falta esperar.

Esta tarea debe hacer que el flujo final sea explícito, seguro y entendible.

## Problemas detectados

1. `Preview` no comunica bien que puede tardar.
2. `Preview` guarda selección automáticamente, haciendo redundante `Confirmar selección`.
3. No queda claro si el usuario debe confirmar antes de generar.
4. `Generar Video preliminar` se siente duplicado con `Preview`.
5. Falta un mensaje claro de salida/descarga cuando el video ya fue generado.

## Decisión de UX

El flujo correcto debe ser:

```txt
1. El usuario elige clips o sube videos locales.
2. El usuario presiona Confirmar selección.
3. Recién entonces se desbloquea Preview.
4. Preview ejecuta el pipeline visual con progreso por fases.
5. Al terminar, se muestra el video y una opción para descargarlo.
```

## Reglas principales

### Confirmar selección

- Debe ser el único botón que guarda `data/selected_assets.json`.
- Debe mostrar éxito claro al guardar.
- Debe marcar en la sesión que la selección fue confirmada.
- Si el usuario cambia opciones después de confirmar, la UI debe pedir confirmar de nuevo o, como mínimo, mostrar que debe confirmar antes de generar preview.

### Preview

- No debe guardar selección automáticamente.
- Debe requerir que exista `data/selected_assets.json`.
- Idealmente debe requerir confirmación en sesión antes de ejecutarse.
- Si falta selección confirmada, debe mostrar:

```txt
Primero confirma la selección de assets.
```

- Debe mostrar un mensaje antes de ejecutar:

```txt
Esto puede demorar entre 2 y 4 minutos según la cantidad y peso de los clips.
```

- Debe mostrar progreso por fases, no porcentaje falso basado en tiempo.

Fases sugeridas:

```txt
1/7 Exportando assets
2/7 Resolviendo assets
3/7 Generando timeline
4/7 Detectando faltantes
5/7 Generando placeholders
6/7 Preparando clips
7/7 Renderizando preview
```

- Debe mostrar éxito o error por fase.
- Si una fase falla, debe detener el flujo y mostrar el error.

### Generar Video preliminar

Para evitar duplicidad, se permite una de estas opciones:

Opción preferida:

- Reemplazar `Generar Video preliminar` por un botón/área de `Descargar video` cuando exista `exports/preview_video.mp4`.

Opción aceptable:

- Mantener `Generar Video preliminar`, pero debe comportarse igual que `Preview` y dejar claro que genera un video preliminar sin audio final.

Para este issue, se prefiere simplificar:

```txt
Confirmar selección
Preview
Descargar video
```

### Descargar video

Si existe:

```txt
exports/preview_video.mp4
```

La UI debe mostrar:

```txt
Video guardado en exports/preview_video.mp4
```

Y, si es posible, mostrar un botón:

```txt
Descargar video
```

usando `st.download_button`.

Si `st.download_button` con el archivo local resulta incómodo o pesado, al menos mostrar claramente la ruta del archivo.

## Reglas técnicas

- Reutilizar funciones existentes.
- No tocar backend interno.
- No modificar parser, classifier, Pexels, scoring, export, resolver, timeline, missing, placeholders, preparation ni rendering.
- No agregar dependencias nuevas.
- No borrar `data/*.json`.
- No borrar outputs de `exports/`.
- Mantener el modo avanzado/debug existente.
- Mantener el sistema funcionando por terminal.

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `panel/guided_flow.py`
- `tests/test_guided_flow.py`
- `README.md`

## No tocar

- `app.py`
- `main.py`
- `panel/streamlit_panel.py`
- `panel/pipeline_control.py`
- `tests/test_pipeline_control.py`
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

- `Confirmar selección` guarda `data/selected_assets.json`.
- `Preview` no guarda selección automáticamente.
- `Preview` muestra error si no existe selección confirmada.
- `Preview` muestra mensaje de espera de 2 a 4 minutos.
- `Preview` muestra progreso por fases.
- El progreso usa pasos reales del pipeline, no porcentaje falso por tiempo.
- Si una fase falla, el flujo se detiene y muestra error claro.
- Al terminar, la UI muestra `exports/preview_video.mp4` con `st.video`.
- Si existe el archivo, se muestra botón `Descargar video` o ruta clara.
- Se elimina o reduce la duplicidad entre `Preview` y `Generar Video preliminar`.
- El modo avanzado/debug sigue disponible.
- No se agregan dependencias nuevas.
- Los tests pasan.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_guided_flow.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Porcentaje real basado en duración de render.
- Jobs en segundo plano.
- Cola de render.
- Notificaciones del sistema.
- Video final con audio.
- Música.
- Subtítulos.
- Transiciones avanzadas.
- Editor notes.
- Rediseño completo adicional de la UI.
