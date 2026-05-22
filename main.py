import argparse
import json
from pathlib import Path

from parser.script_parser import parse_script


try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

SCRIPT_PATH = Path("script.md")
BRIEF_PATH = Path("brief.md")
GENERATED_SCRIPT_PATH = Path("script.generated.md")
DATA_DIR = Path("data")
SCENES_PATH = DATA_DIR / "scenes.json"
VISUAL_PLAN_PATH = DATA_DIR / "visual_plan.json"
PEXELS_RESULTS_PATH = DATA_DIR / "pexels_results.json"
SCORED_RESULTS_PATH = DATA_DIR / "scored_results.json"
PANEL_OUTPUT_PATH = Path("output") / "results_panel.html"


def read_script() -> str:
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"No existe {SCRIPT_PATH}. Crea tu archivo script.md")

    return SCRIPT_PATH.read_text(encoding="utf-8")


def save_json(path: Path, data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def run_generate() -> str:
    from ai.script_generator import GenerationError, generate_script, parse_brief

    if not BRIEF_PATH.exists():
        raise FileNotFoundError(
            f"No existe {BRIEF_PATH}. "
            f"Copia brief.md.example a brief.md y edítalo."
        )

    brief_text = BRIEF_PATH.read_text(encoding="utf-8")
    brief = parse_brief(brief_text)

    print("\n📝 Generando guion a partir de brief.md…")
    print(f"Tema: {brief['topic']}")

    try:
        script_markdown = generate_script(brief)
    except GenerationError as error:
        DATA_DIR.mkdir(exist_ok=True)
        debug_path = DATA_DIR / "last_failed_script.md"

        if error.last_attempt:
            debug_path.write_text(error.last_attempt, encoding="utf-8")
            print(f"\n❌ Último intento guardado en {debug_path} para debug.")

        raise

    GENERATED_SCRIPT_PATH.write_text(script_markdown, encoding="utf-8")

    print("\n✅ Guion generado")
    print(f"Archivo generado: {GENERATED_SCRIPT_PATH}")
    print(
        "Revísalo y, si te convence, renómbralo a script.md "
        "o reemplaza el actual antes de correr parse."
    )

    return script_markdown


def run_parse() -> dict:
    script_text = read_script()
    parsed = parse_script(script_text)

    save_json(SCENES_PATH, parsed)

    print("\n✅ Parser terminado")
    print(f"Proyecto: {parsed['project_title']}")
    print(f"Escenas detectadas: {parsed['scene_count']}")
    print(f"Archivo generado: {SCENES_PATH}")

    for scene in parsed["scenes"]:
        print("-" * 60)
        print(f"Escena {scene['scene']}: {scene['start']} - {scene['end']}")
        print(f"Sección: {scene['section']}")
        print(f"Visual: {scene['visual'][:120]}")

        if scene["warnings"]:
            print("Warnings:")
            for warning in scene["warnings"]:
                print(f"  - {warning}")

    return parsed


def run_classify() -> dict:
    from ai.visual_classifier import classify_visual_scenes

    parsed = load_json(SCENES_PATH)

    visual_plan = classify_visual_scenes(parsed)

    save_json(VISUAL_PLAN_PATH, visual_plan)

    print("\n✅ Clasificación visual terminada")
    print(f"Archivo generado: {VISUAL_PLAN_PATH}")

    for item in visual_plan["visual_plan"]:
        needs_pexels = str(item["needs_pexels"]).lower()
        print(
            f"Escena {item['scene']} → "
            f"{item['asset_type']} → "
            f"needs_pexels {needs_pexels}"
        )
        if item["search_query_en"]:
            print(f"  Query: {item['search_query_en']}")
        print(f"  Acción: {item['primary_action']}")

    return visual_plan


def run_search() -> dict:
    from providers.pexels_provider import search_pexels_for_visual_plan

    visual_plan = load_json(VISUAL_PLAN_PATH)
    pexels_results = search_pexels_for_visual_plan(visual_plan)

    save_json(PEXELS_RESULTS_PATH, pexels_results)

    print("\n✅ Búsqueda en Pexels terminada")
    print(f"Archivo generado: {PEXELS_RESULTS_PATH}")
    print(f"Escenas buscadas: {len(pexels_results['results'])}")

    for item in pexels_results["results"]:
        print("-" * 60)
        print(f"Escena {item['scene']} → {item['asset_type']}")
        print(f"Query: {item['query']}")
        print(f"Sugerencias: {len(item['suggestions'])}")

    return pexels_results


def run_score() -> dict:
    from scoring.video_scorer import score_pexels_results

    pexels_results = load_json(PEXELS_RESULTS_PATH)
    scored_results = score_pexels_results(pexels_results)

    save_json(SCORED_RESULTS_PATH, scored_results)

    print("\n✅ Scoring terminado")
    print(f"Archivo generado: {SCORED_RESULTS_PATH}")

    for item in scored_results["results"]:
        suggestions = item.get("suggestions", [])
        best_score = suggestions[0]["score"] if suggestions else 0
        print(
            f"Escena {item['scene']} → "
            f"{len(suggestions)} sugerencias puntuadas"
        )
        print(f"Mejor score: {best_score}")

    return scored_results


def run_panel() -> dict:
    from panel.results_panel import generate_results_panel

    scored_results = load_json(SCORED_RESULTS_PATH)
    summary = generate_results_panel(scored_results, PANEL_OUTPUT_PATH)

    print("\n✅ Panel generado")
    print(f"Panel generado: {PANEL_OUTPUT_PATH}")
    print(f"Escenas: {summary['scene_count']}")
    print(f"Sugerencias: {summary['suggestion_count']}")

    return summary


def run_all() -> None:
    print("\n🚀 Ejecutando flujo completo")
    run_parse()
    run_classify()
    run_search()
    run_score()


def main():
    parser = argparse.ArgumentParser(
        description="B-roll system: parser + classifier + Pexels search + scoring + panel"
    )

    parser.add_argument(
        "command",
        choices=["generate", "parse", "classify", "search", "score", "panel", "all"],
        help=(
            "generate: brief.md → script.generated.md | "
            "parse: genera scenes.json | "
            "classify: genera visual_plan.json | "
            "search: genera pexels_results.json | "
            "score: genera scored_results.json | "
            "panel: genera output/results_panel.html | "
            "all: ejecuta parse + classify + search + score"
        ),
    )

    args = parser.parse_args()

    if args.command == "generate":
        run_generate()

    if args.command == "parse":
        run_parse()

    if args.command == "classify":
        run_classify()

    if args.command == "search":
        run_search()

    if args.command == "score":
        run_score()

    if args.command == "panel":
        run_panel()

    if args.command == "all":
        run_all()


if __name__ == "__main__":
    main()
