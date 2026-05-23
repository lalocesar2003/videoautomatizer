# PROJECT_PLAN.md

## Objetivo del proyecto

Crear un asistente visual para videos cortos que pueda:

1. Recibir un guion técnico en `script.md` o generarlo desde un prompt libre.
2. Parsear el guion en escenas estructuradas.
3. Clasificar visualmente cada escena con IA.
4. Buscar clips de stock solo cuando corresponda.
5. Puntuar clips sugeridos.
6. Permitir revisión y selección manual en Streamlit.
7. Permitir usar assets locales para escenas propias o grabaciones de pantalla.
8. Resolver escenas faltantes con asset local, stock fallback o placeholder.
9. Generar un timeline según la duración exacta del guion.
10. Preparar clips recortados según cada segmento.
11. Renderizar un video preliminar sin audio final.
12. Generar notas para edición final.

El objetivo del MVP no es producir un video final perfecto, sino un video preliminar visualmente ordenado, listo para agregar voz, música, subtítulos y edición fina.

---

## Flujo general esperado

```txt
Prompt libre o script.md manual
↓
script.md aprobado
↓
data/scenes.json
↓
data/visual_plan.json
↓
data/pexels_results.json
↓
data/scored_results.json
↓
data/selected_assets.json
↓
data/resolved_assets.json
↓
data/timeline.json
↓
exports/prepared_clips/
↓
exports/preview_video.mp4
↓
exports/editor_notes.md
```

````

---

## Fase 1: Parser

### Entrada

- `script.md`

### Salida

- `data/scenes.json`

### Debe extraer

- título
- tiempo de inicio
- tiempo de fin
- duración de escena
- sección
- visual
- audio
- texto en pantalla
- fx
- notas de edición

### Formato oficial

```txt
Guion para TikTok: "Título"

[0:00 - 0:03] EL GANCHO
• Visual: ...
• Texto en pantalla: ...
• Audio: ...
```

### Criterio de éxito

- Detecta todas las escenas.
- Soporta guion normal `-` y guion largo `–`.
- Genera `data/scenes.json`.
- Los tests del parser pasan.

---

## Fase 2: Clasificador visual

### Entrada

- `data/scenes.json`

### Salida

- `data/visual_plan.json`

### Debe clasificar

- `self_recorded`
- `screen_recording`
- `stock`
- `mixed`

### Debe generar

- `scene`
- `asset_type`
- `needs_pexels`
- `primary_action`
- `visual_intent`
- `search_query_en`
- `confidence`
- `reason`

### Reglas

- `self_recorded` → `needs_pexels = false`
- `screen_recording` → `needs_pexels = false`
- `stock` → `needs_pexels = true`
- `mixed` → `needs_pexels = true`

### Criterio de éxito

- Hay una clasificación por cada escena.
- Las escenas `stock` y `mixed` tienen query en inglés.
- Las escenas `self_recorded` y `screen_recording` no buscan en Pexels.

---

## Fase 3: Proveedor de IA configurable

### Objetivo

Permitir elegir el proveedor IA desde `.env`.

### Proveedores previstos

- `ollama`
- `gemini`
- `openai`

### Estado actual

- `ollama`: implementado.
- `gemini`: pendiente.
- `openai`: pendiente.

### Variables esperadas

```env
AI_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

GEMINI_API_KEY=
GEMINI_MODEL=

OPENAI_API_KEY=
OPENAI_MODEL=
```

### Criterio de éxito

- El clasificador usa el proveedor configurado.
- Si el proveedor no existe, falla con mensaje claro.
- Agregar un proveedor no obliga a tocar el clasificador.

---

## Fase 4: Normalizador de visual_plan

### Entrada

- respuesta cruda del proveedor IA

### Salida

- `data/visual_plan.json`

### Objetivo

Asegurar que todos los proveedores devuelvan una estructura uniforme.

### Reglas

- Todo registro debe tener `asset_type`.
- Todo registro debe tener `needs_pexels`.
- Todo registro debe tener `primary_action`.
- Todo registro debe tener `visual_intent`.
- Todo registro debe tener `search_query_en`.
- Todo registro debe tener `confidence`.
- Todo registro debe tener `reason`.
- Si `needs_pexels = false`, `search_query_en = ""`.
- Si `needs_pexels = true`, debe existir query en inglés o fallback razonable.

---

## Fase 5: Pexels Search

### Entrada

- `data/visual_plan.json`

### Salida

- `data/pexels_results.json`

### Solo busca escenas con

- `needs_pexels = true`

### Debe guardar

- provider
- provider_id
- page_url
- preview_url
- thumbnail_url
- duration
- width
- height
- orientation
- author_name
- author_url

### Reglas

- No descarga clips.
- No busca escenas `self_recorded`.
- No busca escenas `screen_recording`.
- Usa `search_query_en`.
- Prioriza formato vertical para TikTok/Reels/Shorts.

---

## Fase 6: Scoring

### Entrada

- `data/pexels_results.json`

### Salida

- `data/scored_results.json`

### Puntaje base

- `+40` si es vertical.
- `+25` si dura entre 4 y 20 segundos.
- `+20` si es HD o superior.
- `+10` si tiene thumbnail.
- `+10` si coincide con intención visual.
- `-30` si es horizontal.
- `-40` si dura demasiado.
- `-50` si tiene logos, marcas o texto visible.

### MVP

En el MVP el scoring será principalmente técnico:

- orientación
- duración
- resolución
- thumbnail

Campos como `semantic_match` y `logo_text_penalty` pueden quedar en 0 hasta implementar scoring multimodal.

### Criterio de éxito

- Cada clip tiene `score`.
- Cada clip tiene `score_breakdown`.
- Cada escena ordena sugerencias de mayor a menor score.
- No llama a Pexels.
- No descarga clips.

---

## Fase 7: Panel interactivo con Streamlit y selección manual

### Entrada

- `data/scored_results.json`

### Salida

- `data/selected_assets.json`

### Debe permitir

- ver escenas
- ver intención visual
- ver query
- ver thumbnails
- abrir `preview_url`
- abrir `page_url`
- revisar score
- revisar `score_breakdown`
- ver duración objetivo de la escena
- ver duración real del clip
- advertir si el clip es más corto que la escena
- seleccionar clips mediante checkbox o botón
- guardar selección en `selected_assets.json`

### Reglas

- No descarga clips.
- No genera ZIP.
- No llama a Pexels.
- No llama a Ollama/Gemini/OpenAI.

---

## Fase 8: Descarga de seleccionados y ZIP

### Entrada

- `data/selected_assets.json`

### Salida

- `exports/clips/`
- `exports/selected_broll.zip`

### Debe permitir

- leer clips seleccionados
- descargar únicamente clips seleccionados
- guardar clips en `exports/clips/`
- nombrar clips por escena
- generar ZIP final
- incluir `selected_assets.json` dentro del ZIP
- opcionalmente incluir `editor_notes.md`

### Reglas

- No descarga clips no seleccionados.
- No vuelve a llamar a Pexels.
- No recorta clips todavía.
- El recorte por duración se hace en una fase posterior.

---

## Fase 9: Assets locales por escena

### Objetivo

Permitir asignar videos locales a escenas.

### Uso

Sirve para:

- escenas `self_recorded`
- escenas `screen_recording`
- grabaciones propias del negocio
- tomas del local
- videos del producto
- clips que Pexels no puede resolver

### Entrada

- archivos locales seleccionados por el usuario

### Salida

- `data/selected_assets.json`

### Estructura esperada

```json
{
  "scene": 3,
  "selected_clip": {
    "provider": "local",
    "local_path": "local_assets/dashboard_susycafe.mp4"
  }
}
```

### Criterio de éxito

- El panel permite asignar asset local por escena.
- `selected_assets.json` soporta `provider = "local"`.
- El exportador y timeline soportan assets locales.

---

## Fase 10: Resolución de escenas sin asset

### Entrada

- `data/scenes.json`
- `data/visual_plan.json`
- `data/selected_assets.json`

### Salida

- `data/resolved_assets.json`

### Objetivo

Antes de generar timeline, cada escena debe tener una resolución.

### Resoluciones posibles

- `pexels`
- `local`
- `fallback_stock`
- `placeholder`
- `missing_asset`

### Debe permitir

Cuando una escena no tenga clip seleccionado:

1. asignar video local
2. usar stock de relleno
3. crear placeholder
4. marcar como pendiente

### Criterio de éxito

- Cada escena tiene una resolución.
- Las escenas sin recurso quedan claramente marcadas.
- El timeline no depende directamente de `selected_assets.json`.

---

## Fase 11: Timeline

### Entrada

- `data/scenes.json`
- `data/visual_plan.json`
- `data/resolved_assets.json`

### Salida

- `data/timeline.json`

### Debe generar

- scene
- start
- end
- duration_seconds
- asset_type
- resolution_type
- clip_path, si existe
- status
- text_on_screen
- audio
- primary_action

### Estados posibles

- `ready`
- `placeholder`
- `fallback_stock`
- `needs_self_recording`
- `needs_screen_recording`
- `missing_asset`
- `needs_manual_review`

### Criterio de éxito

- Calcula duración por escena.
- Ordena escenas correctamente.
- Vincula assets resueltos.
- Marca escenas faltantes o pendientes.

---

## Fase 12: Detectar escenas faltantes o pendientes

### Entrada

- `data/timeline.json`

### Salida

- `data/missing_scenes.json`

### Debe detectar

- escenas sin clip seleccionado
- escenas `self_recorded` sin video local
- escenas `screen_recording` sin video local
- escenas con asset roto o inexistente
- escenas que requieren revisión manual

### Criterio de éxito

- Genera `missing_scenes.json`.
- Explica por qué falta cada escena.
- Sugiere una acción concreta.

---

## Fase 13: Placeholders

### Entrada

- `data/missing_scenes.json`
- `data/timeline.json`

### Salida

- `exports/placeholders/`

### Objetivo

Crear clips placeholder para que el video preliminar no se rompa.

### Ejemplo

```txt
ESCENA 3 FALTANTE
Tipo: screen_recording
Acción: Grabar dashboard de SusyCafe
Duración: 12 segundos
```

### Criterio de éxito

- Crea un placeholder por escena faltante.
- Cada placeholder dura lo mismo que la escena.
- El placeholder puede ser usado en el timeline/render.

---

## Fase 14: Preparar clips según duración del guion

### Entrada

- `data/timeline.json`
- `exports/clips/`
- `exports/placeholders/`

### Salida

- `exports/prepared_clips/`

### Objetivo

Generar versiones preparadas de cada clip con duración exacta según el guion.

### Reglas

- Si `clip_duration > scene_duration`, recortar a `scene_duration`.
- Si `clip_duration == scene_duration`, usar tal cual.
- Si `clip_duration < scene_duration`, marcar warning o usar estrategia configurada.

### Estrategias para clip corto

- `manual_review`
- `placeholder`
- `loop`
- `freeze_last_frame`

### MVP

Para MVP:

- clip corto → `manual_review` o `placeholder`

### Criterio de éxito

- Cada clip preparado dura lo mismo que su escena.
- No modifica clips originales.
- Genera `exports/prepared_clips/`.
- Reporta clips demasiado cortos.

---

## Fase 15: Renderizar video preliminar sin audio final

### Entrada

- `data/timeline.json`
- `exports/prepared_clips/`
- `exports/placeholders/`

### Salida

- `exports/preview_video.mp4`

### Reglas

- No agregar audio final.
- No agregar subtítulos finales.
- No agregar música final.
- Unir clips en el orden del guion.
- Respetar duración exacta de cada escena.
- Usar placeholders cuando falte una escena.

### Criterio de éxito

- Genera `exports/preview_video.mp4`.
- Respeta el orden del guion.
- Respeta `duration_seconds` por escena.
- No falla si hay placeholders.
- El resultado queda listo para agregar audio después.

---

## Fase 16: Editor notes

### Entrada

- `data/scenes.json`
- `data/visual_plan.json`
- `data/resolved_assets.json`
- `data/timeline.json`
- `data/missing_scenes.json`

### Salida

- `exports/editor_notes.md`

### Debe incluir

- proyecto
- escena
- tiempo
- sección
- visual original
- audio sugerido
- texto en pantalla
- clip usado
- asset local usado, si corresponde
- placeholder usado, si corresponde
- escenas que faltan grabar
- acción recomendada por escena

---

## Fase 17: Generador de script.md desde prompt libre

### Entrada

- prompt libre del usuario

Ejemplo:

```txt
Hazme un video de promoción para mi tienda de café llamada SusyCafe.
Duración: 30 segundos.
Estilo: cálido, moderno y familiar.
Objetivo: atraer clientes al local.
```

### Salida

- `script.md`

### Debe generar

Un guion compatible con el parser:

```txt
Guion para TikTok: "Promoción SusyCafe"

[0:00 - 0:03] EL GANCHO
• Visual: ...
• Texto en pantalla: ...
• Audio: ...

[0:03 - 0:08] EL PROBLEMA
• Visual: ...
• Texto en pantalla: ...
• Audio: ...
```

### Reglas

- No llama a Pexels.
- No hace scoring.
- No renderiza video.
- Solo genera o propone `script.md`.

---

## Fase 18: UI Streamlit para prompt, revisión y aprobación

### Entrada

- prompt escrito por el usuario

### Salida

- `script.md` aprobado

### Debe permitir

- escribir prompt libre
- elegir proveedor IA
- definir duración aproximada
- generar guion
- previsualizar `script.md`
- editar el guion antes de guardarlo
- guardar `script.md`
- aprobar y ejecutar pipeline

### Regla clave

El pipeline no debe correr hasta que el usuario apruebe el guion.

---

## Fase 19: Pipeline desde prompt hasta clips puntuados

### Entrada

- prompt libre
- `script.md` aprobado

### Salida

- `data/scored_results.json`

### Flujo

```txt
prompt
↓
script.md generado
↓
revisión/aprobación humana
↓
parse
↓
classify
↓
search
↓
score
```

### Reglas

- No ejecuta Pexels hasta que el usuario apruebe.
- No renderiza video.
- No selecciona clips automáticamente salvo configuración explícita.

---

## Fase 20: Selección automática por mayor score

### Entrada

- `data/scored_results.json`

### Salida

- `data/selected_assets.json`

### Objetivo

Permitir un modo rápido donde el sistema seleccione automáticamente el mejor clip por escena.

### Reglas

- Selecciona el clip con mayor score.
- Si hay empate, toma el primero.
- Si no hay clips, marca escena como `missing_asset`.
- No sobrescribe selección manual sin confirmación.

---

## Fase 21: Flujo completo prompt → video preliminar

### Entrada

- prompt libre

### Salida

- `exports/preview_video.mp4`
- `exports/editor_notes.md`

### Flujo

```txt
prompt
↓
script.md generado
↓
aprobación humana
↓
parse
↓
classify
↓
search
↓
score
↓
selección manual o automática
↓
resolved_assets
↓
timeline
↓
placeholders
↓
prepared_clips
↓
preview_video.mp4
↓
editor_notes.md
```

### Reglas

- No elimina la aprobación humana.
- Permite pausa para selección manual.
- Permite assets locales.
- Usa placeholders si faltan escenas.
- El video generado no tiene audio final.

---

## Fase 22: Configuración central

### Objetivo

Centralizar configuración para evitar valores quemados en código.

### Debe configurar

- `AI_PROVIDER`
- `OLLAMA_MODEL`
- `GEMINI_MODEL`
- `OPENAI_MODEL`
- `PEXELS_API_KEY`
- `CLIPS_PER_SCENE`
- `OUTPUT_RESOLUTION`
- `DATA_DIR`
- `EXPORT_DIR`

### Archivos sugeridos

- `config/settings.py`
- `.env.example`

---

## Fase 23: CLI unificado

### Comandos esperados

```bash
python3 main.py parse
python3 main.py classify
python3 main.py search
python3 main.py score
python3 main.py panel
python3 main.py export
python3 main.py resolve
python3 main.py timeline
python3 main.py placeholders
python3 main.py prepare
python3 main.py render
python3 main.py notes
python3 main.py script
python3 main.py generate
```

### Criterio de éxito

- Cada comando ejecuta una fase.
- Si falta un archivo previo, muestra error claro.
- No ejecuta fases destructivas sin confirmación.

---

## Fase 24: Tests de integración

### Objetivo

Asegurar que el pipeline no se rompa entre fases.

### Debe probar

```txt
script.md
→ parse
→ scenes.json
→ classify mock
→ visual_plan.json
→ search mock
→ pexels_results.json
→ score
→ scored_results.json
```

### Reglas

- No depender de Pexels real.
- No depender de Ollama/Gemini real.
- Usar mocks o fixtures.
- Verificar estructura de JSON intermedios.

---

## Fase 25: Documentación del equipo

### Objetivo

Documentar cómo usar y desarrollar el proyecto.

### Debe incluir

- cómo activar `.venv`
- cómo instalar dependencias
- cómo ejecutar cada fase
- cómo usar Streamlit
- cómo crear branches
- cómo correr tests
- cómo evitar commitear `.venv`
- cómo trabajar con issues
- cómo usar agentes sin romper el repo

```

Este plan ya está alineado con lo que quieres: primero flujo manual asistido y luego flujo completo desde prompt hasta video preliminar.
```
````
