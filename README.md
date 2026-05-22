# videoautomatizer

Asistente de **B-roll automático** para videos cortos (TikTok / Reels / Shorts).

Escribes tu guion en `script.md` y el sistema lo parsea, clasifica visualmente cada escena con IA local, busca clips de stock en Pexels solo donde hacen falta, y los puntúa.

**No** genera video con IA. Solo busca y puntúa stock existente.

## Pipeline

```
script.md
  → parse     → data/scenes.json
  → classify  → data/visual_plan.json
  → search    → data/pexels_results.json
  → score     → data/scored_results.json
```

Cada fase lee/escribe JSON, así que puedes retomar desde cualquier punto.

## Tipos visuales detectados

| Tipo              | Busca Pexels |
|-------------------|--------------|
| `self_recorded`   | No           |
| `screen_recording`| No           |
| `stock`           | Sí           |
| `mixed`           | Sí           |

## Requisitos

- **Python 3.12**
- **[Ollama](https://ollama.com)** corriendo en local (para clasificación visual)
- Un modelo descargado en Ollama, por ejemplo:
  ```bash
  ollama pull llama3.2:3b
  ```
- **API key de Pexels** — gratis en https://www.pexels.com/api/

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
pip install python-dotenv certifi

# 4. Variables de entorno
cp .env.example .env
# edita .env y pon tu PEXELS_API_KEY
```

Contenido de `.env`:

```
PEXELS_API_KEY=tu_api_key_aqui
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## Uso

Escribe tu guion en `script.md` (revisa el ejemplo incluido para el formato: escenas con timestamps `[0:00 - 0:03]`, secciones, y líneas `• Visual:` / `• Texto en pantalla:` / `• Audio:`).

Luego corre las fases:

```bash
python3 main.py parse       # script.md → scenes.json
python3 main.py classify    # → visual_plan.json (necesita Ollama corriendo)
python3 main.py search      # → pexels_results.json (necesita PEXELS_API_KEY)
python3 main.py score       # → scored_results.json
```

O el pipeline inicial completo:

```bash
python3 main.py all         # corre parse + classify
```

> Nota: `all` por ahora solo ejecuta `parse + classify`. `search` y `score` se corren por separado.

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
pip install pytest
pytest
```

Todos los tests usan datos mockeados — no hacen llamadas reales a Pexels ni a Ollama.

## Estructura

```
parser/      script.md → scenes.json
ai/          clasificación visual con LLM (Ollama)
providers/   búsqueda en Pexels
scoring/     puntuación de clips
tests/       un test por módulo
data/        JSON intermedios (gitignored)
script.md    input del usuario
main.py      CLI
```

## Estado

Proyecto en desarrollo. Fuera de alcance por ahora: descarga de clips, visión por IA real, frontend, base de datos.
