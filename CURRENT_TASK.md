# CURRENT_TASK.md

## Tarea actual

Issue #7 — Generar `script.md` automáticamente desde un brief con IA.

## Objetivo

Añadir una fase nueva **antes** de `parse` que toma un `brief.md` (tema,
duración, tono, audiencia, CTA) y produce `script.generated.md` con la
estructura que el parser ya entiende (timestamps, secciones, líneas
`• Visual:` / `• Texto en pantalla:` / `• Audio:`).

El proveedor de IA se elige vía `AI_PROVIDER` en `.env` (issue #5 ya
desbloqueó esto). Solo Ollama está implementado; Gemini queda para un
issue futuro.

## Contexto del proyecto

Flujo nuevo:

brief.md
→ generate            ← fase nueva (este issue)
→ script.generated.md
→ (el usuario lo revisa, lo edita si quiere, y lo renombra a script.md)
→ parser
→ data/scenes.json
→ clasificador visual
→ ...

## Requisitos funcionales

- Nuevo comando `python3 main.py generate` lee `brief.md` y escribe
  `script.generated.md`. **No** sobrescribe `script.md` (lo hace el
  usuario manualmente cuando aprueba el guion).
- El brief usa formato markdown plano con pares `Clave: valor` (igual
  estilo que el resto del proyecto). Campos esperados: tema, plataforma,
  duración objetivo, tono, audiencia, CTA, notas. Solo "tema" es
  obligatorio; el resto da contexto opcional.
- El proveedor se obtiene con `get_provider()` del registro existente.
- El prompt incluye few-shot con al menos un ejemplo de guion válido.
- El output se valida pasándolo por `parse_script()`. Debe:
  - tener al menos una escena,
  - tener `project_title`,
  - no devolver warnings en ninguna escena (todos los campos
    requeridos presentes: start, end, visual, audio, text_on_screen).
- Si la validación falla, reintentar hasta 2 veces más con feedback
  del error al modelo. Si después de 3 intentos sigue mal, fallar
  con un mensaje claro y guardar el último intento en
  `data/last_failed_script.md` para debug.
- Mensajes en español, código y nombres en inglés (convención del repo).

## Archivos permitidos para modificar o crear

- ai/script_generator.py (nuevo)
- main.py (añadir comando `generate`)
- brief.md.example (nuevo)
- tests/test_script_generator.py (nuevo)
- README.md
- CURRENT_TASK.md
- CHANGELOG.md

## No tocar

- parser/script_parser.py
- ai/visual_classifier.py
- ai/ollama_provider.py
- ai/provider_registry.py
- providers/pexels_provider.py
- scoring/video_scorer.py
- panel/*
- selection/*
- app.py
- script.md (lo sigue editando el usuario; el sistema escribe a
  script.generated.md aparte por seguridad)
- .env.example (las vars necesarias ya están desde #5)
- requirements.txt (no se añaden dependencias)
- data/*.json

## Fuera de alcance

- Implementar Gemini de verdad (otro issue, ya planeado).
- A/B testing de variantes de guion.
- Generar imágenes o thumbnails.
- Renombrar automáticamente `script.generated.md` a `script.md`.

## Comando esperado

python3 main.py generate

Lee `brief.md` y escribe `script.generated.md`. Si `brief.md` no existe,
falla con un mensaje claro que recomiende usar `brief.md.example`.
