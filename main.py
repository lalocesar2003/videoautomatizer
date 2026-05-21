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
DATA_DIR = Path("data")
SCENES_PATH = DATA_DIR / "scenes.json"
VISUAL_PLAN_PATH = DATA_DIR / "visual_plan.json"


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


def run_all() -> None:
    run_parse()
    run_classify()


def main():
    parser = argparse.ArgumentParser(
        description="B-roll system: parser + visual classifier"
    )

    parser.add_argument(
        "command",
        choices=["parse", "classify", "all"],
        help="parse: genera scenes.json | classify: genera visual_plan.json | all: ejecuta ambos",
    )

    args = parser.parse_args()

    if args.command == "parse":
        run_parse()

    if args.command == "classify":
        run_classify()

    if args.command == "all":
        run_all()


if __name__ == "__main__":
    main()
