from html import escape
from pathlib import Path
from typing import Any


def generate_results_panel(
    scored_results: dict[str, Any],
    output_path: Path,
) -> dict[str, int]:
    html = render_results_panel(scored_results)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    return {
        "scene_count": len(scored_results.get("results", [])),
        "suggestion_count": count_suggestions(scored_results),
    }


def render_results_panel(scored_results: dict[str, Any]) -> str:
    project_title = clean_text(
        scored_results.get("project_title", "Proyecto sin título")
    )
    format_name = clean_text(scored_results.get("format", ""))
    scenes_html = "\n".join(
        render_scene(scene)
        for scene in scored_results.get("results", [])
    )

    if not scenes_html:
        scenes_html = "<p class=\"empty\">No hay sugerencias puntuadas todavía.</p>"

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(project_title)} · Resultados B-roll</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1117;
      --card: #171b24;
      --muted: #a7adbb;
      --text: #f5f7fb;
      --line: #2a3040;
      --accent: #78d38b;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}

    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}

    header {{
      margin-bottom: 28px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 5vw, 48px);
      letter-spacing: -0.04em;
    }}

    .meta, .muted {{
      color: var(--muted);
    }}

    .scene {{
      border: 1px solid var(--line);
      background: linear-gradient(180deg, #181d28, var(--card));
      border-radius: 18px;
      padding: 18px;
      margin-bottom: 22px;
    }}

    .scene-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 16px;
    }}

    .scene h2 {{
      margin: 0;
      font-size: 22px;
    }}

    .query {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      color: var(--accent);
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 16px;
    }}

    .suggestion {{
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      background: #111520;
    }}

    .thumb {{
      width: 100%;
      aspect-ratio: 9 / 16;
      object-fit: cover;
      background: #0b0d12;
      display: block;
    }}

    .suggestion-body {{
      padding: 12px;
    }}

    .score {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      background: rgba(120, 211, 139, 0.14);
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 8px;
    }}

    dl {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 4px 10px;
      margin: 8px 0 12px;
      font-size: 14px;
    }}

    dt {{ color: var(--muted); }}
    dd {{ margin: 0; }}

    a {{
      color: #91c7ff;
      text-decoration: none;
    }}

    a:hover {{ text-decoration: underline; }}

    .actions {{
      display: flex;
      gap: 8px;
      margin-top: 12px;
    }}

    button {{
      flex: 1;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px;
      color: var(--muted);
      background: #151a25;
      cursor: not-allowed;
    }}

    .breakdown {{
      color: var(--muted);
      font-size: 12px;
      word-break: break-word;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="meta">Panel simple de revisión · {escape(format_name)}</p>
      <h1>{escape(project_title)}</h1>
      <p class="muted">Sugerencias de B-roll puntuadas. Los botones son placeholders; no hay selección real todavía.</p>
    </header>
    {scenes_html}
  </main>
</body>
</html>
"""


def render_scene(scene: dict[str, Any]) -> str:
    suggestions_html = "\n".join(
        render_suggestion(suggestion)
        for suggestion in scene.get("suggestions", [])
    )

    if not suggestions_html:
        suggestions_html = "<p class=\"empty\">Esta escena no tiene sugerencias.</p>"

    return f"""
    <section class="scene">
      <div class="scene-head">
        <div>
          <h2>Escena {escape(clean_text(scene.get("scene")))}</h2>
          <p class="muted">{escape(clean_text(scene.get("asset_type")))}</p>
        </div>
        <div>
          <div class="query">{escape(clean_text(scene.get("query")))}</div>
        </div>
      </div>
      <p><strong>Intención:</strong> {escape(clean_text(scene.get("visual_intent")))}</p>
      <div class="grid">
        {suggestions_html}
      </div>
    </section>
"""


def render_suggestion(suggestion: dict[str, Any]) -> str:
    width = clean_text(suggestion.get("width"))
    height = clean_text(suggestion.get("height"))
    score_breakdown = suggestion.get("score_breakdown", {})

    return f"""
        <article class="suggestion">
          <img class="thumb" src="{escape(clean_text(suggestion.get("thumbnail_url")))}" alt="Thumbnail sugerido">
          <div class="suggestion-body">
            <div class="score">Score {escape(clean_text(suggestion.get("score")))}</div>
            <dl>
              <dt>Orientación</dt><dd>{escape(clean_text(suggestion.get("orientation")))}</dd>
              <dt>Duración</dt><dd>{escape(clean_text(suggestion.get("duration")))}s</dd>
              <dt>Resolución</dt><dd>{escape(width)} × {escape(height)}</dd>
              <dt>Autor</dt><dd>{escape(clean_text(suggestion.get("author_name")))}</dd>
            </dl>
            <p>
              <a href="{escape(clean_text(suggestion.get("page_url")))}" target="_blank" rel="noreferrer">Ver en Pexels</a>
              ·
              <a href="{escape(clean_text(suggestion.get("preview_url")))}" target="_blank" rel="noreferrer">Preview</a>
            </p>
            <p class="breakdown">{escape(format_breakdown(score_breakdown))}</p>
            <div class="actions">
              <button disabled>Seleccionar</button>
              <button disabled>Rebuscar</button>
            </div>
          </div>
        </article>
"""


def count_suggestions(scored_results: dict[str, Any]) -> int:
    return sum(
        len(scene.get("suggestions", []))
        for scene in scored_results.get("results", [])
    )


def format_breakdown(score_breakdown: dict[str, Any]) -> str:
    if not score_breakdown:
        return "Sin breakdown."

    return " · ".join(
        f"{key}: {value}"
        for key, value in score_breakdown.items()
        if value
    ) or "Sin ajustes relevantes."


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()
