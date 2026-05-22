# DECISIONS.md

## Decisión 1: Formato de guion

Usaremos guiones humanos en `script.md`, no JSON manual.

Formato principal:

[0:00 - 0:03] EL GANCHO
• Visual: ...
• Texto en pantalla: ...
• Audio: ...

Motivo:
Es fácil de escribir y suficiente para parsear.

## Decisión 2: Clasificación visual

La clasificación debe hacerla IA, no una lista interminable de IF.

Motivo:
Cada guion puede variar mucho.

## Decisión 3: Pexels

Solo se busca en Pexels si la escena es `stock` o `mixed`.

## Decisión 4: Proveedor de IA configurable

El proveedor de IA se elige en tiempo de ejecución vía la variable
`AI_PROVIDER` en `.env`. El clasificador no sabe ni le importa qué
proveedor está detrás.

Contrato del proveedor (`ai/provider_registry.py`):

```
Provider = Callable[[list[dict[str, str]], dict[str, Any]], dict[str, Any]]
```

Recibe mensajes en formato chat y un schema JSON; devuelve un dict que
cumple ese schema.

Reglas:

- El proveedor activo se obtiene con `get_provider()`.
- Cada proveedor lee sus credenciales de variables de entorno propias
  (ej. `GEMINI_API_KEY`). Nunca se hardcodean ni se loggean.
- Si `AI_PROVIDER` falta, es desconocido, o apunta a un proveedor aún
  no implementado, el sistema falla rápido con un mensaje claro.
- Añadir un proveedor nuevo = añadir un archivo en `ai/` y registrarlo
  en `PROVIDER_FACTORIES`. No se toca el clasificador.

Estado actual:

- `ollama` — implementado.
- `gemini`, `openai` — registrados como placeholders, fallan al
  construirse hasta que se implementen en issues separados.

## Decisión 5: Descarga de clips

Durante las fases de búsqueda y scoring no se descargan clips automáticamente.

Hasta la Fase 4 solo se guardan:

- page_url
- preview_url
- thumbnail_url
- metadata técnica
- score
- score_breakdown

Motivo:
Evitar descargas innecesarias y mantener el flujo rápido mientras se revisan resultados.

## Decisión 6: Exportación manual de clips seleccionados

A partir de la Fase 5B sí se permite descargar clips, pero únicamente cuando hayan sido seleccionados manualmente desde el panel.

Reglas:

- No se descargan todos los clips de Pexels.
- No se descargan clips automáticamente durante la búsqueda.
- Solo se descargan clips presentes en `data/selected_assets.json`.
- La descarga se hace desde `preview_url`.
- Los clips seleccionados se empaquetan en un ZIP local para usarlos en edición.

Motivo:
El objetivo práctico del MVP es revisar previews, seleccionar los clips útiles y tenerlos listos en un ZIP para Premiere, CapCut o DaVinci.
