# CURRENT_TASK.md

## Tarea actual

Issue #27 — Rediseñar Streamlit como flujo guiado de guion y video.

Branch sugerida:

```bash
feature/27-guided-streamlit-flow
```

## Objetivo

Reorganizar la interfaz de Streamlit para que deje de sentirse como una lista técnica de comandos y se convierta en un flujo guiado para el usuario.

La UI debe separar claramente:

```txt
1. Creación / aprobación de guion
2. Creación del video por escenas
3. Acciones finales: Preview y Generar video
```

El backend ya funciona. Esta tarea se enfoca en experiencia, orden visual y conexión limpia con las funciones existentes.

## Contexto importante

El issue #26 agregó un panel técnico de control del pipeline, pero resultó confuso como pantalla principal.

El nuevo diseño debe usar una estructura más humana:

```txt
Crear guion
↓
Revisar escenas por pestañas
↓
Elegir clips / subir videos locales
↓
Preview
↓
Generar video
```

La pantalla técnica del pipeline puede mantenerse, pero debe quedar escondida en una sección tipo:

```txt
Modo avanzado / Debug
```

No debe ser la experiencia principal.

## Referencia visual del usuario

El diseño esperado tiene estas ideas:

1. Una sección “Describe tu guion”.
2. Una sección “Edita tu guion”.
3. Una sección separada para creación del video.
4. Escenas organizadas por pestañas:

```txt
Escena 1 | Escena 2 | Escena 3 | Escena 4 | Escena 5
```

5. Cada escena muestra:

```txt
Tiempo
Sección
Texto en pantalla
Visual
```

6. Si hay clips sugeridos, se muestran como opciones con thumbnail pequeño.
7. Si una escena requiere material manual, debe mostrar claramente una zona para subir video local.
8. Al final deben verse botones claros:

```txt
Preview
Generar Video
```

## Objetivo de producto

El usuario debe poder abrir:

```bash
streamlit run app.py
```

Y entender qué hacer sin conocer los comandos internos.

La UI principal debe responder a esta lógica:

```txt
Primero crea o aprueba el guion.
Luego revisa cada escena.
Luego selecciona clips o sube videos locales.
Luego genera preview/video.
```

## Estructura esperada de la UI

### 1. Sección Crear guion

Debe estar claramente separada de la creación del video.

Debe mostrar:

- título: `Describe tu guion`;
- text area para prompt o idea general;
- botón `Generar Guion`;
- título: `Edita tu guion`;
- text area editable con el guion generado o el contenido actual de `script.md`;
- botón `Aprobar Guion`;
- botón `Regenerar`.

Reglas:

- No ejecutar el pipeline de video hasta que el guion esté aprobado.
- Si la generación automática de guion no está lista para un flujo robusto, se permite que esta sección funcione primero como editor de `script.md`.
- `Aprobar Guion` debe guardar el contenido en `script.md`.
- Después de aprobar, la UI puede permitir ejecutar/generar escenas.

### 2. Sección Crear video

Debe estar separada visualmente de la sección de guion.

Debe mostrar las escenas en pestañas.

Ejemplo:

```txt
Escena 1 | Escena 2 | Escena 3 | Escena 4 | Escena 5
```

Cada pestaña debe mostrar:

- tiempo;
- sección;
- texto en pantalla;
- visual original;
- asset_type si existe;
- estado de la escena;
- acción recomendada.

### 3. Opciones de clips por escena

Si la escena tiene clips sugeridos de Pexels:

- mostrar lista de clips disponibles;
- cada clip debe tener thumbnail pequeño;
- mostrar duración;
- score;
- autor;
- botones/enlaces para abrir preview y Pexels si existen;
- permitir seleccionar máximo un clip por escena.

Regla visual:

- el thumbnail debe ser pequeño, no ocupar toda la pantalla.
- la selección debe ser clara.
- evitar checkboxes múltiples si permiten más de un clip por escena.

Usar preferentemente:

```txt
radio
selectbox
botón de selección única
```

### 4. Escenas sin clips o con tarea manual

Si una escena no tiene clips Pexels o requiere grabación propia:

Debe mostrar claramente:

```txt
Tarea manual requerida
```

Pero NO debe bloquear al usuario.

Debe permitir subir video local.

Ejemplos:

- `self_recorded` → subir video del creador hablando a cámara.
- `screen_recording` → subir grabación de pantalla.
- escena sin sugerencias → subir video propio o dejar pendiente.

La sección de subida debe decir algo como:

```txt
Subir o reemplazar video
```

Y debe guardar la selección como asset local en `data/selected_assets.json`, usando la lógica existente de assets locales.

### 5. Acciones finales

Al final de la sección de video debe haber botones claros:

```txt
Preview
Generar Video
```

#### Botón Preview

Objetivo:

- mostrar `exports/preview_video.mp4` si ya existe;
- o ejecutar lo mínimo necesario para refrescarlo si el usuario ya tiene assets seleccionados.

Para este issue, se permite que `Preview` ejecute:

```txt
export → resolve → timeline → missing → placeholders → prepare → render
```

siempre que exista `data/selected_assets.json`.

#### Botón Generar Video

En este MVP, “Generar Video” puede ejecutar el mismo flujo que Preview y generar:

```txt
exports/preview_video.mp4
```

No debe prometer video final con audio, música o subtítulos.

Puede mostrarse como:

```txt
Generar Video preliminar
```

si eso evita confusión.

## Modo avanzado / Debug

El panel técnico creado en issue #26 puede mantenerse, pero debe quedar debajo de un expander:

```txt
Modo avanzado / Debug
```

Ahí pueden vivir los botones individuales por fase.

La pantalla principal no debe abrir mostrando todos los comandos técnicos.

## Flujo de usuario esperado

```txt
1. Abrir streamlit run app.py
2. Escribir o editar guion
3. Aprobar guion
4. Generar/actualizar escenas si hace falta
5. Revisar escenas por pestañas
6. Seleccionar clip de Pexels o subir video local por escena
7. Confirmar selección
8. Hacer Preview
9. Ver el video preliminar en la UI
```

## Entradas

La UI puede consumir:

```txt
script.md
data/scenes.json
data/visual_plan.json
data/scored_results.json
data/selected_assets.json
exports/preview_video.mp4
```

También puede usar outputs intermedios existentes:

```txt
data/pexels_results.json
data/resolved_assets.json
data/timeline.json
data/missing_scenes.json
exports/placeholders/
exports/prepared_clips/
```

## Salidas

La UI debe poder generar o actualizar:

```txt
script.md
data/selected_assets.json
exports/preview_video.mp4
```

Y, al ejecutar el flujo de preview/video:

```txt
exports/clips/
exports/selected_broll.zip
data/resolved_assets.json
data/timeline.json
data/missing_scenes.json
exports/placeholders/
exports/prepared_clips/
exports/preview_manifest.json
```

## Reglas técnicas

- Reutilizar lógica existente.
- No duplicar selección de assets si ya existe en `selection/asset_selector.py`.
- No duplicar ejecución del pipeline si ya existen runners en `main.py` o `panel/pipeline_control.py`.
- No tocar lógica interna del parser, clasificador, Pexels, scoring, export, resolver, timeline, missing, placeholders, preparation o rendering.
- No agregar dependencias nuevas.
- Mantener compatibilidad con Python 3.12.
- El sistema debe seguir funcionando por terminal.
- La UI no debe borrar `data/*.json`.
- La UI no debe borrar outputs en `exports/`.

## Archivos permitidos para modificar o crear

- `CURRENT_TASK.md`
- `app.py`
- `panel/streamlit_panel.py`
- `panel/guided_flow.py`
- `panel/pipeline_control.py`
- `tests/test_guided_flow.py`
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

- `streamlit run app.py` abre una UI guiada y no un tablero técnico gigante.
- La sección de guion está claramente separada de la sección de video.
- La UI permite editar y aprobar `script.md`.
- La sección de video muestra escenas en pestañas.
- Cada pestaña muestra tiempo, sección, texto en pantalla y visual.
- Los clips sugeridos se muestran con thumbnail pequeño, duración, score y autor.
- Cada escena permite máximo un asset seleccionado.
- Las escenas sin clips o manuales muestran `Tarea manual requerida`.
- Las escenas sin clips o manuales permiten subir video local.
- La selección se guarda en `data/selected_assets.json`.
- Existen botones claros de `Preview` y `Generar Video`.
- Si existe `exports/preview_video.mp4`, se muestra en la UI con `st.video`.
- El modo avanzado/debug existe pero no domina la pantalla principal.
- Los tests pasan.

## Tests esperados

```bash
.venv/bin/python -m pytest tests/test_guided_flow.py
.venv/bin/python -m pytest tests -q
```

Deben pasar.

## Fuera de alcance

- Video final con voz en off.
- Música final.
- Subtítulos finales.
- Transiciones avanzadas.
- Timeline editor drag-and-drop.
- Reordenamiento manual de escenas.
- Selección automática por mejor score.
- Generador de guion perfecto desde prompt libre.
- Next.js.
- Login.
- Pagos.
- Base de datos.
