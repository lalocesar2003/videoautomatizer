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

- `data/scored_results.json`

Salida:

- `data/selected_assets.json`

Esta fase no descarga clips y no genera ZIP. Eso queda para Fase 5B.

Para evitar telemetry de Streamlit al ejecutar:

```bash
streamlit run app.py --browser.gatherUsageStats false
```

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
