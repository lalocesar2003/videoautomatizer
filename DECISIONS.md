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

## Decisión 4: Ollama/OpenAI

El sistema debe permitir usar Ollama local, pero dejar abierta la opción de OpenAI como fallback.

## Decisión 5: Descarga de clips

Por ahora no descargamos clips.
Solo guardamos:

- page_url
- preview_url
- thumbnail_url
