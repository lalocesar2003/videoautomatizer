# videoautomatizer

Asistente de **B-roll automático** para videos cortos (TikTok / Reels / Shorts).

Escribes tu guion en `script.md` y el sistema lo parsea, clasifica visualmente cada escena con IA local, busca clips de stock en Pexels solo donde hacen falta, los puntúa y permite revisar/seleccionar clips desde un panel local con Streamlit.

**No** genera video con IA. Solo busca, puntúa y ayuda a seleccionar stock existente.

## Pipeline

```text
script.md
  → parse     → data/scenes.json
  → classify  → data/visual_plan.json
  → search    → data/pexels_results.json
  → score     → data/scored_results.json
  → panel     → data/selected_assets.json
  → export    → exports/clips/ + exports/selected_broll.zip
  → resolve   → data/resolved_assets.json
  → timeline  → data/timeline.json
  → missing   → data/missing_scenes.json
  → placeholders → exports/placeholders/
  → prepare   → exports/prepared_clips/
  → render    → exports/preview_video.mp4
```

Cada fase lee/escribe JSON, así que puedes retomar desde cualquier punto.

## Tipos visuales detectados

| Tipo               | Busca Pexels |
|--------------------|--------------|
| `self_recorded`    | No           |
| `screen_recording` | No           |
| `stock`            | Sí           |
| `mixed`            | Sí           |

## Requisitos

- **Python 3.12**
- **[Ollama](https://ollama.com)** corriendo en local (para clasificación visual)
- Un modelo descargado en Ollama, por ejemplo:
  ```bash
  ollama pull llama3.2:3b
  ```
- **API key de Pexels** — gratis en https://www.pexels.com/api/
- **Streamlit** para el panel local

## Instalación

```bash
# 1. Clonar
git clone <repo-url>
cd videoautomatizer

# 2. Entorno virtual
python3 -m venv .venv
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env
# edita .env y pon tu PEXELS_API_KEY
```

Contenido de `.env`:

```env
PEXELS_API_KEY=tu_api_key_aqui
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## Uso

Escribe tu guion en `script.md` con el formato:

```text
[0:00 - 0:03] EL GANCHO
• Visual: ...
• Texto en pantalla: ...
• Audio: ...
```

Luego corre las fases:

```bash
python3 main.py parse       # script.md → scenes.json
python3 main.py classify    # → visual_plan.json (necesita Ollama corriendo)
python3 main.py search      # → pexels_results.json (necesita PEXELS_API_KEY)
python3 main.py score       # → scored_results.json
```

### Opcional: generar `script.md` con IA

Si no quieres escribir el guion a mano, puedes generarlo a partir de un
brief corto:

```bash
cp brief.md.example brief.md
# edita brief.md con tu tema, tono, audiencia, CTA
python3 main.py generate    # → script.generated.md
```

Revísalo. Si te convence, renómbralo a `script.md` (o reemplaza el
existente) y continúa con `parse`.

Notas:

- Usa el proveedor de IA configurado en `AI_PROVIDER` (hoy solo `ollama`).
- Modelos chicos como `llama3.2:3b` tienden a copiar el ejemplo del
  prompt. Para guiones de calidad real, conviene un modelo más grande
  (`llama3.1:8b` o superior) o un proveedor externo cuando esté
  implementado.
- El guion generado se valida automáticamente con `parse_script()`. Si
  el formato falla, se reintenta 2 veces más antes de fallar con un
  archivo de debug en `data/last_failed_script.md`.

O el pipeline completo en CLI:

```bash
python3 main.py all         # parse + classify + search + score
```

## Panel Streamlit

La Fase 5A abre un panel local para revisar clips puntuados y guardar selección manual:

```bash
streamlit run app.py
```

Entrada:

- `data/scenes.json`
- `data/visual_plan.json`
- `data/scored_results.json`

Salida:

- `data/selected_assets.json`

El panel permite elegir un clip de Pexels, dejar la escena como tarea manual
o subir un video propio como asset local. Cada escena admite máximo un asset
seleccionado.

Los videos locales se guardan en:

```text
local_assets/
```

Estructura esperada para un asset local en `data/selected_assets.json`:

```json
{
  "scene": 3,
  "selection_type": "local",
  "selected_clip": {
    "provider": "local",
    "local_path": "local_assets/scene_03_dashboard_demo.mp4",
    "original_filename": "dashboard_demo.mp4"
  }
}
```

Esta fase no descarga clips y no genera ZIP.

Para evitar telemetry de Streamlit al ejecutar:

```bash
streamlit run app.py --browser.gatherUsageStats false
```

## Exportar clips seleccionados

Después de guardar `data/selected_assets.json` desde el panel:

```bash
python3 main.py export
```

El exportador:

- descarga clips de Pexels usando `preview_url`;
- copia assets locales desde `local_path`;
- ignora escenas marcadas como `manual_task`;
- genera `exports/clips/`;
- genera `exports/selected_broll.zip`;
- incluye una copia de `selected_assets.json` dentro del ZIP.

## Resolver assets por escena

Antes de generar un timeline, cada escena debe tener una resolución clara:
Pexels, local, fallback stock, placeholder o pendiente.

```bash
python3 main.py resolve
```

Entrada:

- `data/scenes.json`
- `data/visual_plan.json`
- `data/selected_assets.json`

Salida:

- `data/resolved_assets.json`

Opcionalmente puedes crear `data/resolution_choices.json` para forzar una
decisión por escena sin crear UI nueva todavía:

```json
{
  "resolutions": [
    {
      "scene": 3,
      "resolution_type": "placeholder",
      "message": "Usar placeholder hasta grabar el dashboard."
    }
  ]
}
```

Esta fase no llama a Pexels, no llama a IA, no descarga clips y no renderiza
video.

## Generar timeline

El timeline ordena las escenas por tiempo, calcula duración por segmento y
vincula cada escena con su asset resuelto o estado pendiente.

```bash
python3 main.py timeline
```

Entrada:

- `data/scenes.json`
- `data/visual_plan.json`
- `data/resolved_assets.json`

Salida:

- `data/timeline.json`

Esta fase no descarga clips, no copia archivos, no crea placeholders, no
recorta clips y no renderiza video. Solo deja el mapa temporal listo para las
siguientes fases.

## Detectar escenas faltantes

El reporte de faltantes audita `data/timeline.json` y muestra qué escenas no
están listas para render automático.

```bash
python3 main.py missing
```

Entrada:

- `data/timeline.json`

Salida:

- `data/missing_scenes.json`

Detecta escenas pendientes (`needs_self_recording`, `needs_screen_recording`,
`needs_manual_review`, `needs_fallback_search`, `missing_asset`) y escenas
marcadas como listas cuyo `clip_path` no existe localmente.

Esta fase no descarga clips, no crea placeholders, no modifica el timeline y no
renderiza video.

## Generar placeholders

Los placeholders son clips simples para que el render preliminar no se rompa
cuando falte una escena o un archivo todavía no exista localmente.

```bash
python3 main.py placeholders
```

Entrada:

- `data/missing_scenes.json`
- `data/timeline.json`

Salida:

- `exports/placeholders/`
- `exports/placeholders/placeholder_manifest.json`

Requiere `ffmpeg` instalado. Esta fase no descarga clips, no modifica el
timeline, no recorta assets reales y no renderiza el video final.


## Preparar clips por duración

Esta fase toma el timeline y genera una versión lista de cada escena con la
duración exacta del guion.

```bash
python3 main.py prepare
```

Entrada:

- `data/timeline.json`
- `exports/clips/`
- `exports/placeholders/`

Salida:

- `exports/prepared_clips/`
- `exports/prepared_clips/prepared_manifest.json`

Reglas principales:

- si el clip es más largo que la escena, lo recorta;
- si el clip tiene duración suficiente, genera `scene_XX_ready.mp4`;
- si falta el clip real, usa el placeholder de esa escena cuando exista;
- si el clip es demasiado corto y no hay placeholder, lo reporta como warning.

Requiere `ffmpeg` y `ffprobe` instalados. Esta fase no descarga clips, no llama
a Pexels, no llama a IA y no renderiza el video preliminar final.


## Renderizar video preliminar

Después de preparar clips, puedes unir las escenas en un primer video de revisión:

```bash
python3 main.py render
```

Entrada:

- `data/timeline.json`
- `exports/prepared_clips/`
- `exports/placeholders/`

Salida:

- `exports/preview_video.mp4`
- `exports/preview_manifest.json`

El render usa `scene_XX_ready.mp4` cuando existe y cae al placeholder de la
misma escena si falta el clip preparado. Normaliza los clips a formato vertical
`1080x1920`, 24 fps, H.264 y sin audio para que la concatenación sea estable.

Esta fase no agrega voz, música, subtítulos ni transiciones avanzadas. Es un
preview visual listo para revisar antes de la edición final.

## Reglas de scoring

Cada clip de Pexels se puntúa así:

| Regla                          | Puntos |
|--------------------------------|--------|
| Vertical                       | +40    |
| Duración 4-20 s                | +25    |
| HD (≥1080)                     | +20    |
| Tiene thumbnail                | +10    |
| `semantic_match` (placeholder) | +10    |
| Horizontal                     | -30    |
| Duración > 20 s                | -40    |
| Logos/texto (placeholder)      | -50    |

`semantic_match` y `has_logo_or_text` son placeholders manuales por ahora (sin visión por IA todavía).

## Tests

```bash
python3 -m unittest discover -s tests
```

Todos los tests usan datos mockeados — no hacen llamadas reales a Pexels ni a Ollama.

## Estructura

```text
parser/       script.md → scenes.json
ai/           clasificación visual con LLM (Ollama)
providers/    búsqueda en Pexels
scoring/      puntuación de clips
selection/    selección manual de clips
panel/        panel Streamlit
tests/        tests por módulo
data/         JSON intermedios (gitignored)
script.md     input del usuario
main.py       CLI
app.py        panel Streamlit
```

## Estado

Proyecto en desarrollo. Fuera de alcance por ahora: montaje automático de video, visión por IA real, login, pagos y base de datos.
