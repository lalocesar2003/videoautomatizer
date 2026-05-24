# DECISIONS.md

## Decisión 1: Formato de guion

Usaremos guiones humanos en `script.md`, no JSON manual.

Formato principal:

```txt
[0:00 - 0:03] EL GANCHO
• Visual: ...
• Texto en pantalla: ...
• Audio: ...
```

Motivo:

Es fácil de escribir, fácil de revisar manualmente y suficiente para que el parser extraiga escenas, tiempos, visuales, texto en pantalla y audio.

Reglas:

- El usuario puede escribir o editar manualmente `script.md`.
- La IA también puede generar `script.md`, pero debe respetar exactamente este formato.
- El parser no debe depender de JSON escrito manualmente por el usuario.
- El campo `Visual` es clave para clasificar la escena y decidir si se busca stock, se requiere grabación propia o se necesita pantalla.

## Decisión 2: Clasificación visual

La clasificación visual debe hacerla IA, no una lista interminable de `if`.

Motivo:

Cada guion puede variar mucho. La IA permite interpretar mejor la intención visual de cada escena.

Tipos permitidos:

- `self_recorded`: el creador sale en cámara, habla, señala, sostiene celular o hace CTA.
- `screen_recording`: se graba pantalla, dashboard, Excel, WhatsApp, interfaz, modal, cursor o demo.
- `stock`: se necesita un clip externo de stock.
- `mixed`: combina grabación propia o pantalla con apoyo de stock.

Reglas:

- `self_recorded` → `needs_pexels = false`
- `screen_recording` → `needs_pexels = false`
- `stock` → `needs_pexels = true`
- `mixed` → `needs_pexels = true`

## Decisión 3: Pexels

Solo se busca en Pexels si la escena es `stock` o `mixed`.

No se busca en Pexels cuando la escena es:

- `self_recorded`
- `screen_recording`

Motivo:

No tiene sentido buscar stock para escenas donde el creador debe aparecer en cámara o donde debe grabarse una pantalla/interfaz real.

Reglas:

- Pexels se usa solo después de que exista `data/visual_plan.json`.
- Pexels usa `search_query_en`.
- Las búsquedas deben estar en inglés.
- En búsqueda solo se guardan URLs y metadata; no se descargan clips.
- La descarga queda reservada para clips ya seleccionados.

## Decisión 4: Proveedor de IA configurable

El proveedor de IA se elige en tiempo de ejecución vía la variable `AI_PROVIDER` en `.env`.

El clasificador no sabe ni le importa qué proveedor está detrás.

Contrato del proveedor (`ai/provider_registry.py`):

```python
Provider = Callable[[list[dict[str, str]], dict[str, Any]], dict[str, Any]]
```

Recibe mensajes en formato chat y un schema JSON; devuelve un dict que cumple ese schema.

Reglas:

- El proveedor activo se obtiene con `get_provider()`.
- Cada proveedor lee sus credenciales de variables de entorno propias.
- Nunca se hardcodean credenciales.
- Nunca se loggean API keys.
- Si `AI_PROVIDER` falta, es desconocido o apunta a un proveedor no implementado, el sistema falla rápido con un mensaje claro.
- Añadir un proveedor nuevo significa añadir un archivo en `ai/` y registrarlo en `PROVIDER_FACTORIES`.
- No se debe tocar el clasificador para añadir nuevos proveedores.

Estado actual:

- `ollama`: implementado.
- `gemini`: pendiente.
- `openai`: pendiente.

## Decisión 5: Normalización del visual_plan

El sistema debe normalizar siempre la salida del clasificador IA antes de guardar `data/visual_plan.json`.

Motivo:

Diferentes proveedores de IA pueden devolver estructuras ligeramente distintas. El resto del pipeline necesita un contrato estable.

Reglas:

- Todo registro debe tener `asset_type`.
- Todo registro debe tener `needs_pexels`.
- Todo registro debe tener `primary_action`.
- Todo registro debe tener `visual_intent`.
- Todo registro debe tener `search_query_en`.
- Todo registro debe tener `confidence`.
- Todo registro debe tener `reason`.
- Si `asset_type` es `self_recorded` o `screen_recording`, entonces `needs_pexels = false` y `search_query_en = ""`.
- Si `asset_type` es `stock` o `mixed`, entonces `needs_pexels = true`.
- Si `needs_pexels = true` y falta `search_query_en`, se debe usar fallback razonable.

## Decisión 6: Descarga de clips

Durante las fases de búsqueda y scoring no se descargan clips automáticamente.

Hasta la Fase 6 solo se guardan:

- `page_url`
- `preview_url`
- `thumbnail_url`
- metadata técnica
- `score`
- `score_breakdown`

Motivo:

Evitar descargas innecesarias y mantener el flujo rápido mientras se revisan resultados.

Reglas:

- `search` no descarga clips.
- `score` no descarga clips.
- El panel Streamlit no descarga clips durante la selección.
- La descarga solo ocurre cuando el usuario ya seleccionó clips.

## Decisión 7: Exportación manual de clips seleccionados

A partir de la fase de exportación sí se permite descargar clips, pero únicamente cuando hayan sido seleccionados manualmente desde el panel.

Reglas:

- No se descargan todos los clips de Pexels.
- No se descargan clips automáticamente durante la búsqueda.
- Solo se descargan clips presentes en `data/selected_assets.json`.
- La descarga se hace desde `preview_url`.
- Los clips seleccionados se guardan en `exports/clips/`.
- Los clips seleccionados también se empaquetan en un ZIP local.
- El ZIP debe incluir una copia de `selected_assets.json`.

Motivo:

El objetivo práctico del MVP es revisar previews, seleccionar clips útiles y tenerlos listos para Premiere, CapCut, DaVinci u otro editor.

## Decisión 8: Prompt libre no ejecuta el pipeline sin aprobación humana

El flujo desde prompt libre debe incluir revisión humana antes de ejecutar la lógica completa.

Flujo correcto:

```txt
prompt libre
↓
IA genera script.md
↓
usuario revisa / edita / aprueba script.md
↓
recién ahí se ejecuta parse → classify → search → score
```

Reglas:

- La IA puede generar `script.md`.
- El usuario debe poder revisar el guion antes de sobrescribir `script.md`.
- El usuario debe aprobar antes de ejecutar el pipeline.
- El sistema no debe ejecutar automáticamente Pexels ni scoring apenas se genera un guion.
- El botón correcto en Streamlit debe ser algo como “Aprobar y ejecutar pipeline”.

Motivo:

El guion define toda la estructura visual, tiempos, búsqueda de clips y render. Ejecutar todo sin revisión puede generar resultados malos o gastar recursos innecesarios.

## Decisión 9: La duración del guion manda

Cada escena del video preliminar debe respetar la duración definida en el guion.

Ejemplo:

```txt
[0:00 - 0:03] EL GANCHO
```

Esa escena debe durar 3 segundos en el video preliminar.

Reglas:

- Si el clip seleccionado dura más que la escena, se recorta.
- Si el clip seleccionado dura igual que la escena, se usa completo.
- Si el clip seleccionado dura menos que la escena, se marca para revisión o se resuelve con placeholder/relleno según configuración.
- Los clips originales no se modifican.
- El sistema debe generar versiones preparadas en `exports/prepared_clips/`.

Motivo:

El video final debe encajar con el guion y con el audio que se grabará después. La duración de cada segmento no debe depender de la duración original del clip de Pexels.

## Decisión 10: Panel debe mostrar ajuste de duración

El panel de selección debe mostrar si un clip encaja con la duración de la escena.

Debe mostrar:

- duración objetivo de la escena
- duración real del clip
- si el clip alcanza
- si el clip sobra
- si el clip es más corto que la escena

Ejemplo:

```txt
Escena 1: 0:00 - 0:03
Duración objetivo: 3s
Clip: 12s
Estado: OK, se puede recortar.
```

Reglas:

- El usuario debe poder ver si el clip sirve antes de seleccionarlo.
- Si el clip es más corto que la escena, debe aparecer advertencia.
- Esta validación no reemplaza el scoring, pero ayuda a elegir mejor.

## Decisión 11: Assets locales

El sistema debe permitir asignar videos locales a escenas.

Motivo:

No todas las escenas se pueden resolver con Pexels. Algunas requieren:

- grabación del creador
- grabación del local
- grabación de pantalla
- demostración de un producto real
- toma propia del negocio

Estructura esperada:

```json
{
  "scene": 3,
  "selected_clip": {
    "provider": "local",
    "local_path": "local_assets/dashboard_susycafe.mp4"
  }
}
```

Reglas:

- `selected_assets.json` debe soportar `provider = "pexels"`.
- `selected_assets.json` debe soportar `provider = "local"`.
- El sistema debe diferenciar claramente assets descargados de Pexels y assets locales.
- El exportador y el timeline deben poder usar ambos tipos.

## Decisión 12: Resolución de escenas antes del timeline

Antes de generar el timeline final, cada escena debe tener una resolución.

Resoluciones posibles:

- `pexels`
- `local`
- `fallback_stock`
- `placeholder`
- `missing_asset`

El sistema no debe renderizar directamente desde `selected_assets.json`.

Debe pasar por:

```txt
selected_assets.json
↓
resolved_assets.json
↓
timeline.json
```

Motivo:

`selected_assets.json` solo dice qué eligió el usuario. Pero para renderizar se necesita saber qué hacer con todas las escenas, incluso con las que no tienen clip seleccionado.

## Decisión 13: Escenas sin asset

Cuando una escena no tenga asset seleccionado, el sistema debe permitir elegir cómo resolverla.

Opciones:

- Subir/asignar video local.
- Usar stock de relleno.
- Crear placeholder.
- Marcar como pendiente.

Reglas:

- Si una escena `self_recorded` no tiene video local, se debe marcar como pendiente o placeholder.
- Si una escena `screen_recording` no tiene video local, se debe marcar como pendiente o placeholder.
- Si el usuario elige “usar stock de relleno”, debe quedar registrado como `fallback_stock`.
- No se debe buscar stock de relleno automáticamente sin decisión explícita o sin una tarea separada.
- Si no hay recurso, el render debe usar placeholder para no romper el video preliminar.

## Decisión 14: No renderizar sin resolver escenas

El render preliminar solo debe ejecutarse cuando exista `data/timeline.json`.

El timeline debe indicar para cada escena:

- `ready`
- `placeholder`
- `fallback_stock`
- `needs_self_recording`
- `needs_screen_recording`
- `missing_asset`
- `needs_manual_review`

Reglas:

- El render no debe fallar si hay escenas faltantes.
- Si falta una escena, se usa placeholder.
- Si una escena tiene asset local o de Pexels preparado, se usa ese asset.
- Si una escena requiere grabación manual, debe quedar visible en `editor_notes.md`.

Motivo:

El objetivo del MVP no es producir un video final perfecto, sino un video preliminar ordenado y editable.

## Decisión 15: Video preliminar sin audio final

El sistema debe generar un video preliminar sin audio final.

Reglas:

- No agregar voz final.
- No agregar música final.
- No agregar subtítulos finales.
- No hacer edición fina.
- No reemplazar el trabajo del editor.
- Solo unir los segmentos visuales según el guion.

Salida esperada:

```txt
exports/preview_video.mp4
```

Motivo:

El usuario agregará después voz, música, cortes finos, subtítulos, efectos y correcciones en el editor de video.

## Decisión 16: Placeholders

Si una escena no tiene asset disponible, el sistema debe generar un placeholder visual.

Ejemplo:

```txt
ESCENA 3 FALTANTE
Tipo: screen_recording
Acción: Grabar dashboard de SusyCafe
Duración: 12 segundos
```

Reglas:

- El placeholder debe durar lo mismo que la escena.
- Debe indicar claramente qué falta.
- Debe poder usarse dentro del render preliminar.
- Debe guardarse en `exports/placeholders/`.

Motivo:

El video preliminar no debe romperse por una escena faltante. El placeholder permite mantener la duración y el orden del guion.

## Decisión 17: Editor notes

El sistema debe generar un archivo `editor_notes.md` para facilitar la edición final.

Debe incluir:

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

Salida esperada:

```txt
exports/editor_notes.md
```

Motivo:

Aunque el sistema genere un video preliminar, el usuario necesita instrucciones claras para completar la edición final.

## Decisión 18: Scoring multimodal es opcional, no bloqueante

El scoring multimodal con visión IA es una mejora futura, no una dependencia del MVP.

Motivo:

El scoring técnico actual permite avanzar con revisión manual desde Streamlit.

Reglas:

- `semantic_match` puede quedar en 0 en el MVP.
- `logo_text_penalty` puede quedar en 0 en el MVP.
- La detección de logos, texto visible o coincidencia semántica visual se implementará después.
- Si se implementa, debe ser opt-in mediante variable de entorno.

Ejemplo:

```env
SCORING_MULTIMODAL=false
```

## Decisión 19: Flujo manual asistido primero

El primer objetivo útil del sistema es el modo manual asistido.

Flujo:

```txt
script.md manual o aprobado
↓
parse
↓
classify
↓
search
↓
score
↓
panel Streamlit
↓
selección manual
↓
export ZIP
↓
timeline
↓
render preliminar
```

Motivo:

Este flujo es más controlable, menos frágil y permite validar si los clips sugeridos realmente sirven antes de automatizar todo.

## Decisión 20: Flujo automático completo después

El flujo automático completo desde prompt hasta video preliminar será una fase posterior.

Flujo futuro:

```txt
prompt libre
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
render preliminar
```

Reglas:

- No debe eliminar la revisión humana del guion.
- Debe permitir pausa para selección manual.
- Debe permitir selección automática por mayor score solo si el usuario lo confirma.
- Debe permitir assets locales.
- Debe generar placeholders si faltan escenas.

## Decisión 21: Una escena solo puede tener un asset principal seleccionado

Cada escena del guion debe tener como máximo un asset principal seleccionado para el render preliminar.

Motivo:

El timeline necesita saber qué recurso visual usará cada segmento. Si una escena tiene varios clips seleccionados, el render no sabrá cuál usar.

Reglas:

- Una escena puede tener 0 o 1 asset principal.
- Si no tiene asset, se resolverá después como local, fallback_stock, placeholder o missing_asset.
- El panel debe usar radio button o selectbox por escena.
- `selected_assets.json` no debe tener dos assets principales para la misma escena.

## Decisión 22: El panel debe mostrar todas las escenas

El panel no debe mostrar solo escenas con clips de Pexels.

Debe mostrar:

- escenas con clips sugeridos
- escenas sin clips sugeridos
- escenas self_recorded
- escenas screen_recording
- escenas pendientes de acción manual

Motivo:

El usuario necesita revisar el video completo, no solo los segmentos que Pexels pudo resolver.
