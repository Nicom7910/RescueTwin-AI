import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.autonomous.mission_runner import AutonomousMissionRunner


DEFAULT_OUTPUT_DIR = Path("reports/unity_demo_scenarios")
DEFAULT_Q_TABLE_PATH = Path("models/autonomous/q_table.json")
DEFAULT_UNITY_DIR = Path("unity/RescueTwinUnity_v2")


def clean_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    patterns = [
        "mission_*_trajectory.json",
        "mission_*_world.json",
        "mission_*_known_map.txt",
        "autonomous_summary.json",
        "experience_log.csv",
        "unity_demo_manifest.json",
        "candidate_summary.json",
    ]

    for pattern in patterns:
        for file_path in output_dir.glob(pattern):
            file_path.unlink()


def generate_candidates(
    candidates: int,
    max_steps: int,
    seed: Optional[int],
    output_dir: Path,
    q_table_path: Path,
    verbose: bool,
) -> Dict:
    runner = AutonomousMissionRunner(
        output_dir=output_dir,
        q_table_path=q_table_path,
        seed=seed,
    )

    return runner.run(
        episodes=candidates,
        max_steps=max_steps,
        training=False,
        verbose=verbose,
    )


def load_trajectory(output_dir: Path, episode: int) -> List[Dict]:
    path = output_dir / f"mission_{episode:03d}_trajectory.json"

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_world(output_dir: Path, episode: int) -> Dict:
    path = output_dir / f"mission_{episode:03d}_world.json"

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def count_return_steps(trajectory: List[Dict]) -> int:
    return sum(1 for step in trajectory if step.get("return_to_base_mode") is True)


def count_escape_steps(trajectory: List[Dict]) -> int:
    return sum(1 for step in trajectory if step.get("escape_mode") is True)


def count_medium_or_high_risk_steps(trajectory: List[Dict]) -> int:
    return sum(
        1
        for step in trajectory
        if step.get("risk_level") in {"MEDIO", "ALTO"}
    )


def count_world_risk_cells(world: Dict) -> int:
    return len(world.get("risk_cells", []))


def classify_candidate(summary: Dict, trajectory: List[Dict], world: Dict) -> str:
    victims_found = summary.get("victims_found", 0)
    finish_reason = summary.get("finish_reason", "")
    return_steps = count_return_steps(trajectory)
    escape_steps = count_escape_steps(trajectory)
    risk_steps = count_medium_or_high_risk_steps(trajectory)
    risk_cells = count_world_risk_cells(world)
    visited_ratio = summary.get("visited_ratio", 0)

    if victims_found > 0 or finish_reason == "all_victims_found":
        return "victim"

    if finish_reason == "returned_base_low_battery" and return_steps >= 5:
        return "return"

    if escape_steps >= 2:
        return "escape"

    if risk_steps >= 8 or risk_cells >= 10:
        return "risk"

    if visited_ratio >= 0.08:
        return "exploration"

    return "general"
def count_position_revisits(trajectory: List[Dict]) -> int:
    positions = [(step.get("x"), step.get("y")) for step in trajectory]
    seen = set()
    revisits = 0

    for position in positions:
        if position in seen:
            revisits += 1
        else:
            seen.add(position)

    return revisits


def count_immediate_backtracks(trajectory: List[Dict]) -> int:
    """
    Cuenta patrones A-B-A, típicos de ida y vuelta.
    """

    if len(trajectory) < 3:
        return 0

    backtracks = 0

    for index in range(2, len(trajectory)):
        position_now = (trajectory[index].get("x"), trajectory[index].get("y"))
        position_two_steps_ago = (
            trajectory[index - 2].get("x"),
            trajectory[index - 2].get("y"),
        )

        if position_now == position_two_steps_ago:
            backtracks += 1

    return backtracks


def candidate_score(summary: Dict, trajectory: List[Dict], world: Dict, category: str) -> float:
    victims_found = summary.get("victims_found", 0)
    visited_ratio = summary.get("visited_ratio", 0)
    total_reward = summary.get("total_reward", 0)
    steps = summary.get("steps", 0)

    return_steps = count_return_steps(trajectory)
    escape_steps = count_escape_steps(trajectory)
    risk_steps = count_medium_or_high_risk_steps(trajectory)
    risk_cells = count_world_risk_cells(world)

    revisits = count_position_revisits(trajectory)
    backtracks = count_immediate_backtracks(trajectory)

    loop_penalty = revisits * 12 + backtracks * 35

    if category == "victim":
        return (
            victims_found * 1200
            + risk_steps * 12
            + visited_ratio * 1200
            + steps * 3
            - loop_penalty
        )

    if category == "return":
        return (
            return_steps * 70
            + visited_ratio * 1200
            + steps * 2
            - loop_penalty
        )

    if category == "escape":
        return (
            escape_steps * 90
            + risk_steps * 10
            + visited_ratio * 900
            + steps
            - loop_penalty
        )

    if category == "risk":
        return (
            risk_steps * 70
            + risk_cells * 8
            + visited_ratio * 1200
            - loop_penalty
        )

    if category == "exploration":
        return (
            visited_ratio * 1800
            + steps * 3
            + max(total_reward, -500) * 0.05
            - loop_penalty
        )

    return visited_ratio * 1000 + steps - loop_penalty


def build_candidate_table(summary_report: Dict, output_dir: Path) -> List[Dict]:
    candidates = []

    for item in summary_report.get("summaries", []):
        episode = item["episode"]
        trajectory = load_trajectory(output_dir, episode)
        world = load_world(output_dir, episode)

        category = classify_candidate(item, trajectory, world)

        candidates.append(
            {
                "episode": episode,
                "category": category,
                "score": candidate_score(item, trajectory, world, category),
                "summary": item,
                "trajectory": trajectory,
                "world": world,
                "return_steps": count_return_steps(trajectory),
                "escape_steps": count_escape_steps(trajectory),
                "risk_steps": count_medium_or_high_risk_steps(trajectory),
                "risk_cells": count_world_risk_cells(world),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def select_diverse_scenarios(candidates: List[Dict], selected_count: int) -> List[Dict]:
    selected = []

    preferred_order = [
        "victim",
        "return",
        "exploration",
        "risk",
        "escape",
        "general",
    ]

    used_episodes = set()

    for category in preferred_order:
        if len(selected) >= selected_count:
            break

        options = [
            item
            for item in candidates
            if item["category"] == category and item["episode"] not in used_episodes
        ]

        if not options:
            continue

        chosen = options[0]
        selected.append(chosen)
        used_episodes.add(chosen["episode"])

    if len(selected) < selected_count:
        for candidate in candidates:
            if len(selected) >= selected_count:
                break

            if candidate["episode"] in used_episodes:
                continue

            selected.append(candidate)
            used_episodes.add(candidate["episode"])

    return selected[:selected_count]


def title_for_category(category: str, summary: Dict) -> str:
    if category == "victim":
        return "Detección de posible víctima en zona de riesgo"

    if category == "return":
        return "Retorno automático a base por batería baja"

    if category == "escape":
        return "Escape ante estancamiento operacional"

    if category == "risk":
        return "Exploración en zona de riesgo ambiental"

    if category == "exploration":
        return "Exploración autónoma en zona de derrumbe"

    finish_reason = summary.get("finish_reason", "")

    if finish_reason == "returned_base_low_battery":
        return "Retorno automático a base por batería baja"

    return "Misión autónoma RescueTwin"


def description_for_category(category: str, summary: Dict) -> str:
    if category == "victim":
        return (
            "El robot recorre el mapa procedural y detecta una posible víctima. "
            "Permite mostrar la relación entre sensores, riesgo y decisión autónoma."
        )

    if category == "return":
        return (
            "El robot explora el entorno, detecta batería baja y activa el modo retorno. "
            "La ruta de regreso se calcula automáticamente mediante planificación hacia la base."
        )

    if category == "escape":
        return (
            "El robot queda temporalmente estancado ante obstáculos y activa el modo escape. "
            "Esta capa evita bucles y permite retomar la exploración."
        )

    if category == "risk":
        return (
            "El robot atraviesa sectores con riesgo medio o alto, representados por celdas de riesgo "
            "calculadas desde gas, temperatura, vibración e inclinación."
        )

    if category == "exploration":
        return (
            "El robot realiza una exploración autónoma del entorno, evitando obstáculos, "
            "registrando riesgo percibido y trazando su recorrido."
        )

    return (
        "Misión autónoma generada proceduralmente para visualizar el comportamiento del agente."
    )


def copy_selected_files(
    selected: List[Dict],
    output_dir: Path,
) -> List[Dict]:
    scenarios = []

    for new_index, item in enumerate(selected, start=1):
        original_episode = item["episode"]
        summary = item["summary"]
        category = item["category"]

        source_trajectory = output_dir / f"mission_{original_episode:03d}_trajectory.json"
        source_world = output_dir / f"mission_{original_episode:03d}_world.json"
        source_map = output_dir / f"mission_{original_episode:03d}_known_map.txt"

        target_trajectory = output_dir / f"demo_{new_index:03d}_trajectory.json"
        target_world = output_dir / f"demo_{new_index:03d}_world.json"
        target_map = output_dir / f"demo_{new_index:03d}_known_map.txt"

        with source_trajectory.open("r", encoding="utf-8") as file:
            original_trajectory = json.load(file)

        smoothed_trajectory = smooth_trajectory_for_unity(original_trajectory)

        target_trajectory.write_text(
            json.dumps(smoothed_trajectory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        shutil.copy2(source_world, target_world)

        if source_map.exists():
            shutil.copy2(source_map, target_map)

        scenario = {
            "demo": new_index,
            "source_mission": original_episode,
            "category": category,
            "title": title_for_category(category, summary),
            "description": description_for_category(category, summary),
            "trajectory_file": str(target_trajectory),
            "world_file": str(target_world),
            "known_map_file": str(target_map),
            "steps": summary.get("steps"),
            "total_reward": summary.get("total_reward"),
            "victims_found": summary.get("victims_found"),
            "remaining_victims": summary.get("remaining_victims"),
            "visited_ratio": summary.get("visited_ratio"),
            "battery_final": summary.get("battery_final"),
            "finish_reason": summary.get("finish_reason"),
            "return_steps": item.get("return_steps"),
            "escape_steps": item.get("escape_steps"),
            "risk_steps": item.get("risk_steps"),
            "risk_cells": item.get("risk_cells"),
        }

        scenarios.append(scenario)

    manifest_path = output_dir / "unity_demo_manifest.json"
    manifest_path.write_text(
        json.dumps(scenarios, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return scenarios


def copy_to_unity_streaming_assets(
    output_dir: Path,
    unity_dir: Path,
    scenarios: List[Dict],
) -> None:
    streaming_assets_dir = unity_dir / "Assets" / "StreamingAssets"
    streaming_assets_dir.mkdir(parents=True, exist_ok=True)

    for scenario in scenarios:
        demo = scenario["demo"]

        source_trajectory = output_dir / f"demo_{demo:03d}_trajectory.json"
        source_world = output_dir / f"demo_{demo:03d}_world.json"

        target_trajectory = streaming_assets_dir / source_trajectory.name
        target_world = streaming_assets_dir / source_world.name

        if source_trajectory.exists():
            shutil.copy2(source_trajectory, target_trajectory)

        if source_world.exists():
            shutil.copy2(source_world, target_world)

    manifest_path = output_dir / "unity_demo_manifest.json"

    if manifest_path.exists():
        shutil.copy2(
            manifest_path,
            streaming_assets_dir / "unity_demo_manifest.json",
        )


def print_summary(
    scenarios: List[Dict],
    candidates: List[Dict],
    output_dir: Path,
    unity_dir: Optional[Path],
    copied_to_unity: bool,
) -> None:
    print("\n" + "=" * 96)
    print("ESCENARIOS DEMO PARA UNITY SELECCIONADOS")
    print("=" * 96)
    print()

    print("Candidatos generados por categoría:")
    categories = {}

    for candidate in candidates:
        categories[candidate["category"]] = categories.get(candidate["category"], 0) + 1

    for category, count in sorted(categories.items()):
        print(f"- {category}: {count}")

    print()

    for scenario in scenarios:
        print(f"Demo {scenario['demo']:03d}: {scenario['title']}")
        print(f"  Categoría: {scenario['category']}")
        print(f"  Misión original: {scenario['source_mission']:03d}")
        print(f"  Descripción: {scenario['description']}")
        print(f"  Pasos: {scenario['steps']}")
        print(f"  Recompensa total: {scenario['total_reward']}")
        print(f"  Víctimas encontradas: {scenario['victims_found']}")
        print(f"  Pasos retorno: {scenario['return_steps']}")
        print(f"  Pasos escape: {scenario['escape_steps']}")
        print(f"  Pasos riesgo medio/alto: {scenario['risk_steps']}")
        print(f"  Celdas de riesgo en mundo: {scenario['risk_cells']}")
        print(f"  Motivo de finalización: {scenario['finish_reason']}")
        print()

    print("Archivos demo generados:")
    print(f"- {output_dir / 'unity_demo_manifest.json'}")

    for scenario in scenarios:
        demo = scenario["demo"]
        print(f"- {output_dir / f'demo_{demo:03d}_trajectory.json'}")
        print(f"- {output_dir / f'demo_{demo:03d}_world.json'}")

    if copied_to_unity and unity_dir is not None:
        streaming_assets_dir = unity_dir / "Assets" / "StreamingAssets"
        print()
        print("Archivos copiados a Unity:")
        print(f"- {streaming_assets_dir}")

    print()
    print("Para probar en Unity:")
    print()
    print("Demo 001:")
    print("  MissionReplayController → Mission File Name = demo_001_trajectory.json")
    print("  MissionMapBuilder       → World File Name   = demo_001_world.json")
    print()
    print("Demo 002:")
    print("  MissionReplayController → Mission File Name = demo_002_trajectory.json")
    print("  MissionMapBuilder       → World File Name   = demo_002_world.json")
    print()
    print("Demo 003:")
    print("  MissionReplayController → Mission File Name = demo_003_trajectory.json")
    print("  MissionMapBuilder       → World File Name   = demo_003_world.json")


def smooth_trajectory_for_unity(trajectory: List[Dict]) -> List[Dict]:
    """
    Limpia micro-bucles visuales del tipo A-B-A.

    No cambia el aprendizaje ni la simulación original.
    Solo genera una trayectoria más clara para la demo Unity.
    """

    if len(trajectory) < 3:
        return trajectory

    smoothed = []

    for step in trajectory:
        smoothed.append(step)

        while len(smoothed) >= 3:
            a = smoothed[-3]
            b = smoothed[-2]
            c = smoothed[-1]

            pos_a = (a.get("x"), a.get("y"))
            pos_c = (c.get("x"), c.get("y"))

            is_backtrack = pos_a == pos_c

            # No eliminamos pasos críticos.
            critical_step = (
                b.get("victim_found") is True
                or b.get("return_to_base_mode") is True
                or b.get("escape_mode") is True
            )

            if is_backtrack and not critical_step:
                smoothed.pop(-2)
            else:
                break

    # Reenumerar steps para que el HUD sea claro.
    for index, step in enumerate(smoothed, start=1):
        step["step"] = index

    return smoothed

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera y selecciona escenarios demo variados para Unity."
    )

    parser.add_argument(
        "--candidates",
        type=int,
        default=20,
        help="Cantidad de misiones candidatas a generar.",
    )

    parser.add_argument(
        "--selected",
        type=int,
        default=3,
        help="Cantidad de demos finales a seleccionar.",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=120,
        help="Cantidad máxima de pasos por misión.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla para generar escenarios reproducibles.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Carpeta donde se guardan los escenarios generados.",
    )

    parser.add_argument(
        "--q-table",
        type=Path,
        default=DEFAULT_Q_TABLE_PATH,
        help="Ruta a la Q-table entrenada.",
    )

    parser.add_argument(
        "--unity-dir",
        type=Path,
        default=DEFAULT_UNITY_DIR,
        help="Ruta al proyecto Unity.",
    )

    parser.add_argument(
        "--no-copy-unity",
        action="store_true",
        help="No copiar automáticamente los JSON a Assets/StreamingAssets.",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Ejecutar sin imprimir logs detallados de cada misión.",
    )

    args = parser.parse_args()

    clean_output_dir(args.output_dir)

    summary_report = generate_candidates(
        candidates=args.candidates,
        max_steps=args.max_steps,
        seed=args.seed,
        output_dir=args.output_dir,
        q_table_path=args.q_table,
        verbose=not args.quiet,
    )

    candidate_summary_path = args.output_dir / "candidate_summary.json"
    candidate_summary_path.write_text(
        json.dumps(summary_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    candidates = build_candidate_table(summary_report, args.output_dir)
    selected = select_diverse_scenarios(candidates, args.selected)
    scenarios = copy_selected_files(selected, args.output_dir)

    copied_to_unity = False

    if not args.no_copy_unity:
        copy_to_unity_streaming_assets(
            output_dir=args.output_dir,
            unity_dir=args.unity_dir,
            scenarios=scenarios,
        )
        copied_to_unity = True

    print_summary(
        scenarios=scenarios,
        candidates=candidates,
        output_dir=args.output_dir,
        unity_dir=args.unity_dir,
        copied_to_unity=copied_to_unity,
    )


if __name__ == "__main__":
    main()