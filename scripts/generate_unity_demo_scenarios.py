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

    for pattern in [
        "mission_*_trajectory.json",
        "mission_*_world.json",
        "mission_*_known_map.txt",
        "demo_*_trajectory.json",
        "demo_*_world.json",
        "demo_*_mission_report.md",
        "unity_demo_manifest.json",
        "mission_reports_index.md",
        "experience_log.csv",
        "autonomous_summary.json",
    ]:
        for file_path in output_dir.glob(pattern):
            file_path.unlink()


def generate_candidates(
    output_dir: Path,
    q_table_path: Path,
    candidates: int,
    max_steps: int,
    seed: Optional[int],
    quiet: bool,
) -> Dict:
    runner = AutonomousMissionRunner(
        output_dir=output_dir,
        q_table_path=q_table_path,
        seed=seed,
    )

    report = runner.run(
        episodes=candidates,
        max_steps=max_steps,
        training=False,
        verbose=not quiet,
    )

    return report


def load_json(path: Path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_trajectory(candidate: Dict) -> List[Dict]:
    path = Path(candidate["trajectory_file"])
    data = load_json(path)

    if isinstance(data, list):
        return data

    return []


def load_world(candidate: Dict) -> Dict:
    path = Path(candidate["world_file"])
    data = load_json(path)

    if isinstance(data, dict):
        return data

    return {}


def count_return_steps(trajectory: List[Dict]) -> int:
    return sum(1 for step in trajectory if step.get("return_to_base_mode") is True)


def count_victim_search_steps(trajectory: List[Dict]) -> int:
    return sum(1 for step in trajectory if step.get("victim_search_mode") is True)


def count_medium_or_high_risk_steps(trajectory: List[Dict]) -> int:
    return sum(
        1
        for step in trajectory
        if step.get("risk_level") in {"MEDIO", "ALTO"}
    )


def count_world_risk_cells(world: Dict) -> int:
    risk_cells = world.get("risk_cells", [])

    if not isinstance(risk_cells, list):
        return 0

    return len(risk_cells)


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
    if len(trajectory) < 3:
        return 0

    backtracks = 0

    for index in range(2, len(trajectory)):
        position_now = (
            trajectory[index].get("x"),
            trajectory[index].get("y"),
        )
        position_two_steps_ago = (
            trajectory[index - 2].get("x"),
            trajectory[index - 2].get("y"),
        )

        if position_now == position_two_steps_ago:
            backtracks += 1

    return backtracks


def classify_candidate(summary: Dict, trajectory: List[Dict], world: Dict) -> str:
    victims_found = summary.get("victims_found", 0)
    finish_reason = summary.get("finish_reason", "")

    if victims_found > 0 or finish_reason == "all_victims_found":
        return "victim"

    if finish_reason == "returned_base_low_battery" and count_return_steps(trajectory) >= 5:
        return "return"

    return "other"


def candidate_score(
    summary: Dict,
    trajectory: List[Dict],
    world: Dict,
    category: str,
) -> float:
    victims_found = summary.get("victims_found", 0)
    visited_ratio = summary.get("visited_ratio", 0)
    steps = summary.get("steps", 0)
    total_reward = summary.get("total_reward", 0)

    return_steps = count_return_steps(trajectory)
    victim_search_steps = count_victim_search_steps(trajectory)
    risk_steps = count_medium_or_high_risk_steps(trajectory)
    risk_cells = count_world_risk_cells(world)

    revisits = count_position_revisits(trajectory)
    backtracks = count_immediate_backtracks(trajectory)

    loop_penalty = revisits * 12 + backtracks * 35

    if category == "victim":
        return (
            victims_found * 1500
            + victim_search_steps * 90
            + risk_steps * 20
            + visited_ratio * 1200
            + steps * 2
            - loop_penalty
        )

    if category == "return":
        return (
            return_steps * 100
            + visited_ratio * 1000
            + steps * 2
            + max(total_reward, -800) * 0.05
            - loop_penalty
        )

    return visited_ratio * 500 + steps - loop_penalty


def build_candidate_table(report: Dict) -> List[Dict]:
    candidates = []

    for summary in report.get("summaries", []):
        trajectory = load_trajectory(summary)
        world = load_world(summary)
        category = classify_candidate(summary, trajectory, world)

        candidate = {
            "summary": summary,
            "trajectory": trajectory,
            "world": world,
            "category": category,
            "score": candidate_score(summary, trajectory, world, category),
            "return_steps": count_return_steps(trajectory),
            "victim_search_steps": count_victim_search_steps(trajectory),
            "risk_steps": count_medium_or_high_risk_steps(trajectory),
            "risk_cells": count_world_risk_cells(world),
            "revisits": count_position_revisits(trajectory),
            "backtracks": count_immediate_backtracks(trajectory),
        }

        candidates.append(candidate)

    return candidates


def select_best_by_category(
    candidates: List[Dict],
    category: str,
    already_selected_episodes: set,
) -> Optional[Dict]:
    filtered = [
        candidate
        for candidate in candidates
        if candidate["category"] == category
        and candidate["summary"].get("episode") not in already_selected_episodes
    ]

    if not filtered:
        return None

    return sorted(filtered, key=lambda item: item["score"], reverse=True)[0]


def select_two_scenarios(candidates: List[Dict]) -> List[Dict]:
    selected = []
    selected_episodes = set()

    for category in ["victim", "return"]:
        candidate = select_best_by_category(candidates, category, selected_episodes)

        if candidate is not None:
            selected.append(candidate)
            selected_episodes.add(candidate["summary"].get("episode"))

    if len(selected) < 2:
        remaining = [
            candidate
            for candidate in candidates
            if candidate["summary"].get("episode") not in selected_episodes
        ]
        remaining = sorted(remaining, key=lambda item: item["score"], reverse=True)

        for candidate in remaining:
            selected.append(candidate)
            selected_episodes.add(candidate["summary"].get("episode"))

            if len(selected) == 2:
                break

    return selected[:2]


def smooth_trajectory_for_unity(trajectory: List[Dict]) -> List[Dict]:
    if len(trajectory) < 3:
        return trajectory

    smoothed = []

    for step in trajectory:
        smoothed.append(dict(step))

        while len(smoothed) >= 3:
            a = smoothed[-3]
            b = smoothed[-2]
            c = smoothed[-1]

            pos_a = (a.get("x"), a.get("y"))
            pos_c = (c.get("x"), c.get("y"))

            is_backtrack = pos_a == pos_c

            critical_step = (
                b.get("victim_found") is True
                or b.get("return_to_base_mode") is True
                or b.get("victim_search_mode") is True
            )

            if is_backtrack and not critical_step:
                smoothed.pop(-2)
            else:
                break

    for index, step in enumerate(smoothed, start=1):
        step["step"] = index

    return smoothed


def title_for_category(category: str) -> str:
    titles = {
        "victim": "Detección de posible víctima en zona de riesgo",
        "return": "Retorno automático a base por batería baja",
        "other": "Escenario autónomo general",
    }

    return titles.get(category, "Escenario autónomo general")


def description_for_category(category: str) -> str:
    descriptions = {
        "victim": (
            "El robot explora el mapa procedural, detecta una posible víctima "
            "y registra su ubicación. Permite mostrar la relación entre sensores, "
            "riesgo y decisión autónoma."
        ),
        "return": (
            "El robot explora el entorno, detecta batería baja y activa el modo "
            "retorno. La ruta de regreso se calcula automáticamente hacia la base."
        ),
        "other": (
            "El robot ejecuta una misión autónoma sobre un entorno procedural, "
            "tomando decisiones según sensores, riesgo y batería."
        ),
    }

    return descriptions.get(category, descriptions["other"])


def format_bool(value) -> str:
    if value is True:
        return "Sí"

    if value is False:
        return "No"

    return "-"


def action_explanation(action: str) -> str:
    explanations = {
        "AVANZAR": "El robot intenta avanzar hacia la siguiente celda.",
        "RETROCEDER": "El robot retrocede para salir de una zona poco conveniente.",
        "GIRAR_IZQUIERDA": "El robot gira hacia la izquierda para reorientarse.",
        "GIRAR_DERECHA": "El robot gira hacia la derecha para reorientarse.",
        "ESCANEAR": "El robot escanea el entorno para confirmar señales o riesgo.",
        "ENVIAR_ALERTA": "El robot envía una alerta a la base.",
        "VOLVER_BASE": "El robot prioriza el retorno seguro a la base.",
    }

    return explanations.get(action, "Acción autónoma ejecutada por el agente.")


def mode_for_step(step: Dict) -> str:
    if step.get("return_to_base_mode") is True:
        return "RETORNO A BASE"

    if step.get("victim_search_mode") is True:
        return "BÚSQUEDA DE VÍCTIMA"

    if step.get("victim_found") is True:
        return "VÍCTIMA LOCALIZADA"

    return "EXPLORACIÓN"


def extract_key_events(trajectory: List[Dict]) -> List[str]:
    events = []

    previous_mode = None

    for step in trajectory:
        current_mode = mode_for_step(step)

        if current_mode != previous_mode:
            events.append(
                f"Paso {step.get('step')}: cambio de modo a **{current_mode}** "
                f"en posición ({step.get('x')}, {step.get('y')})."
            )
            previous_mode = current_mode

        if step.get("victim_detected") is True:
            target_x = step.get("victim_target_x")
            target_y = step.get("victim_target_y")

            if target_x is not None and target_y is not None:
                events.append(
                    f"Paso {step.get('step')}: se detecta posible víctima y se define "
                    f"objetivo ({target_x}, {target_y})."
                )
            else:
                events.append(
                    f"Paso {step.get('step')}: se detecta señal de posible víctima."
                )

        if step.get("victim_found") is True:
            events.append(
                f"Paso {step.get('step')}: víctima localizada en "
                f"({step.get('victim_x')}, {step.get('victim_y')})."
            )

        if step.get("return_to_base_mode") is True:
            events.append(
                f"Paso {step.get('step')}: se activa o mantiene retorno a base."
            )

    compact_events = []
    seen = set()

    for event in events:
        if event not in seen:
            compact_events.append(event)
            seen.add(event)

    return compact_events[:25]


def generate_mission_report(
    output_dir: Path,
    demo_id: str,
    demo_index: int,
    candidate: Dict,
    smoothed_trajectory: List[Dict],
    target_trajectory: Path,
    target_world: Path,
) -> Path:
    summary = candidate["summary"]
    category = candidate["category"]
    world = candidate["world"]

    report_path = output_dir / f"{demo_id}_mission_report.md"

    risk_cells = world.get("risk_cells", [])
    obstacles = world.get("obstacles", [])
    victims = world.get("victims", [])

    title = title_for_category(category)
    description = description_for_category(category)

    key_events = extract_key_events(smoothed_trajectory)

    lines = []

    lines.append(f"# Informe de misión Unity - Demo {demo_index:03d}")
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")
    lines.append(description)
    lines.append("")
    lines.append("## Archivos asociados")
    lines.append("")
    lines.append(f"- Trayectoria Unity: `{target_trajectory.name}`")
    lines.append(f"- Mundo Unity: `{target_world.name}`")
    lines.append("")
    lines.append("## Resumen ejecutivo")
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---|---:|")
    lines.append(f"| Categoría | {category} |")
    lines.append(f"| Episodio original | {summary.get('episode')} |")
    lines.append(f"| Pasos originales | {summary.get('steps')} |")
    lines.append(f"| Pasos visualizados en Unity | {len(smoothed_trajectory)} |")
    lines.append(f"| Recompensa total | {summary.get('total_reward')} |")
    lines.append(f"| Víctimas encontradas | {summary.get('victims_found')} |")
    lines.append(f"| Víctimas restantes | {summary.get('remaining_victims')} |")
    lines.append(f"| Colisiones | {summary.get('collisions')} |")
    lines.append(f"| Porcentaje de exploración | {summary.get('visited_ratio')} |")
    lines.append(f"| Batería final | {summary.get('battery_final')} |")
    lines.append(f"| Motivo de finalización | {summary.get('finish_reason')} |")
    lines.append(f"| Celdas de riesgo del mundo | {len(risk_cells)} |")
    lines.append(f"| Obstáculos del mundo | {len(obstacles)} |")
    lines.append(f"| Víctimas iniciales del mundo | {len(victims)} |")
    lines.append(f"| Pasos en búsqueda de víctima | {count_victim_search_steps(smoothed_trajectory)} |")
    lines.append(f"| Pasos en retorno a base | {count_return_steps(smoothed_trajectory)} |")
    lines.append(f"| Pasos con riesgo medio/alto | {count_medium_or_high_risk_steps(smoothed_trajectory)} |")
    lines.append(f"| Revisitas de posición | {count_position_revisits(smoothed_trajectory)} |")
    lines.append(f"| Backtracks A-B-A | {count_immediate_backtracks(smoothed_trajectory)} |")
    lines.append("")

    last_victim_location = summary.get("last_victim_location")

    if last_victim_location:
        lines.append("## Víctima localizada")
        lines.append("")
        lines.append(
            f"La última víctima localizada por el robot se registró en la posición "
            f"**({last_victim_location['x']}, {last_victim_location['y']})**."
        )
        lines.append("")

    lines.append("## Eventos relevantes")
    lines.append("")

    if key_events:
        for event in key_events:
            lines.append(f"- {event}")
    else:
        lines.append("- No se registraron eventos críticos destacados.")

    lines.append("")
    lines.append("## Decisiones del robot paso a paso")
    lines.append("")
    lines.append(
        "| Paso | Posición | Acción | Modo | Riesgo | Batería | Víctima detectada | Víctima localizada | Objetivo víctima | Decisión |"
    )
    lines.append(
        "|---:|---:|---|---|---|---|---|---|---|---|"
    )

    for step in smoothed_trajectory:
        action = step.get("action", "-")
        mode = mode_for_step(step)

        target_x = step.get("victim_target_x")
        target_y = step.get("victim_target_y")

        if target_x is not None and target_y is not None:
            target_text = f"({target_x}, {target_y})"
        else:
            target_text = "-"

        lines.append(
            f"| {step.get('step')} "
            f"| ({step.get('x')}, {step.get('y')}) "
            f"| {action} "
            f"| {mode} "
            f"| {step.get('risk_level', '-')} "
            f"| {step.get('battery_level', '-')} "
            f"| {format_bool(step.get('victim_detected'))} "
            f"| {format_bool(step.get('victim_found'))} "
            f"| {target_text} "
            f"| {action_explanation(action)} |"
        )

    lines.append("")
    lines.append("## Interpretación de la misión")
    lines.append("")

    if category == "victim":
        lines.append(
            "La misión evidencia que el agente autónomo no solo explora el entorno, "
            "sino que también reacciona ante señales de posible víctima. Cuando la señal "
            "aparece, se activa el modo de búsqueda de víctima y el robot prioriza dirigirse "
            "hacia el objetivo detectado."
        )
    elif category == "return":
        lines.append(
            "La misión evidencia la capa de seguridad del sistema. Cuando la batería entra "
            "en un estado crítico, el robot activa el modo retorno a base y prioriza llegar "
            "a una zona segura antes de continuar explorando."
        )
    else:
        lines.append(
            "La misión muestra el comportamiento autónomo general del agente en un entorno "
            "procedural, tomando decisiones en función de sensores, riesgo, batería y mapa."
        )

    lines.append("")
    lines.append("## Nota")
    lines.append("")
    lines.append(
        "Este informe fue generado automáticamente a partir de los archivos JSON utilizados "
        "por Unity. La trayectoria puede estar suavizada visualmente para eliminar micro-bucles "
        "A-B-A, sin modificar la lógica base de la simulación."
    )
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    return report_path


def generate_reports_index(output_dir: Path, manifest_demos: List[Dict]) -> Path:
    index_path = output_dir / "mission_reports_index.md"

    lines = []
    lines.append("# Índice de informes de misión Unity")
    lines.append("")
    lines.append("Este archivo resume los informes generados automáticamente para los escenarios de Unity.")
    lines.append("")
    lines.append("| Demo | Categoría | Informe | Trayectoria | Mundo |")
    lines.append("|---:|---|---|---|---|")

    for demo in manifest_demos:
        report_file = demo.get("mission_report_file", "-")
        lines.append(
            f"| {demo['demo']:03d} "
            f"| {demo['category']} "
            f"| `{report_file}` "
            f"| `{demo['trajectory_file']}` "
            f"| `{demo['world_file']}` |"
        )

    lines.append("")
    lines.append("Demos disponibles en Unity:")
    lines.append("")
    lines.append("- Tecla `1`: demo víctima/riesgo.")
    lines.append("- Tecla `2`: demo retorno a base.")
    lines.append("- Tecla `R`: reiniciar demo actual.")
    lines.append("")

    index_path.write_text("\n".join(lines), encoding="utf-8")

    return index_path


def copy_selected_files(selected: List[Dict], output_dir: Path) -> List[Dict]:
    manifest_demos = []

    for index, candidate in enumerate(selected, start=1):
        demo_id = f"demo_{index:03d}"

        source_trajectory = Path(candidate["summary"]["trajectory_file"])
        source_world = Path(candidate["summary"]["world_file"])

        target_trajectory = output_dir / f"{demo_id}_trajectory.json"
        target_world = output_dir / f"{demo_id}_world.json"

        original_trajectory = load_json(source_trajectory)

        if not isinstance(original_trajectory, list):
            original_trajectory = []

        smoothed_trajectory = smooth_trajectory_for_unity(original_trajectory)

        target_trajectory.write_text(
            json.dumps(smoothed_trajectory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        shutil.copy2(source_world, target_world)

        mission_report_path = generate_mission_report(
            output_dir=output_dir,
            demo_id=demo_id,
            demo_index=index,
            candidate=candidate,
            smoothed_trajectory=smoothed_trajectory,
            target_trajectory=target_trajectory,
            target_world=target_world,
        )

        summary = candidate["summary"]
        category = candidate["category"]

        manifest_demos.append(
            {
                "demo": index,
                "category": category,
                "title": title_for_category(category),
                "description": description_for_category(category),
                "source_episode": summary.get("episode"),
                "trajectory_file": target_trajectory.name,
                "world_file": target_world.name,
                "mission_report_file": mission_report_path.name,
                "steps": len(smoothed_trajectory),
                "original_steps": summary.get("steps"),
                "total_reward": summary.get("total_reward"),
                "victims_found": summary.get("victims_found"),
                "remaining_victims": summary.get("remaining_victims"),
                "return_steps": candidate["return_steps"],
                "victim_search_steps": candidate["victim_search_steps"],
                "risk_steps": candidate["risk_steps"],
                "risk_cells": candidate["risk_cells"],
                "revisits": candidate["revisits"],
                "backtracks": candidate["backtracks"],
                "finish_reason": summary.get("finish_reason"),
                "last_victim_location": summary.get("last_victim_location"),
            }
        )

    generate_reports_index(output_dir, manifest_demos)

    manifest = {
        "description": "Escenarios demo seleccionados para Unity",
        "selected_demos": len(manifest_demos),
        "demos": manifest_demos,
    }

    manifest_path = output_dir / "unity_demo_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest_demos


def remove_old_demo_three_from_unity(streaming_assets_dir: Path) -> None:
    for file_name in [
        "demo_003_trajectory.json",
        "demo_003_trajectory.json.meta",
        "demo_003_world.json",
        "demo_003_world.json.meta",
    ]:
        file_path = streaming_assets_dir / file_name

        if file_path.exists():
            file_path.unlink()


def copy_to_unity_streaming_assets(
    output_dir: Path,
    unity_dir: Path,
    manifest_demos: List[Dict],
) -> Path:
    streaming_assets_dir = unity_dir / "Assets" / "StreamingAssets"
    streaming_assets_dir.mkdir(parents=True, exist_ok=True)

    remove_old_demo_three_from_unity(streaming_assets_dir)

    for demo in manifest_demos:
        for key in ["trajectory_file", "world_file"]:
            source = output_dir / demo[key]
            target = streaming_assets_dir / demo[key]
            shutil.copy2(source, target)

    shutil.copy2(
        output_dir / "unity_demo_manifest.json",
        streaming_assets_dir / "unity_demo_manifest.json",
    )

    return streaming_assets_dir


def print_summary(
    candidates: List[Dict],
    manifest_demos: List[Dict],
    output_dir: Path,
    unity_streaming_assets: Optional[Path],
) -> None:
    category_counts = {}

    for candidate in candidates:
        category = candidate["category"]
        category_counts[category] = category_counts.get(category, 0) + 1

    print("\n" + "=" * 96)
    print("ESCENARIOS DEMO PARA UNITY SELECCIONADOS")
    print("=" * 96)

    print("\nCandidatos generados por categoría:")

    for category, count in sorted(category_counts.items()):
        print(f"- {category}: {count}")

    for demo in manifest_demos:
        print(f"\nDemo {demo['demo']:03d}: {demo['title']}")
        print(f"  Categoría: {demo['category']}")
        print(f"  Misión original: {demo['source_episode']:03d}")
        print(f"  Descripción: {demo['description']}")
        print(f"  Pasos Unity: {demo['steps']}")
        print(f"  Pasos originales: {demo['original_steps']}")
        print(f"  Recompensa total: {demo['total_reward']}")
        print(f"  Víctimas encontradas: {demo['victims_found']}")
        print(f"  Víctimas restantes: {demo['remaining_victims']}")
        print(f"  Pasos búsqueda víctima: {demo['victim_search_steps']}")
        print(f"  Pasos retorno: {demo['return_steps']}")
        print(f"  Pasos riesgo medio/alto: {demo['risk_steps']}")
        print(f"  Celdas de riesgo en mundo: {demo['risk_cells']}")
        print(f"  Revisitas: {demo['revisits']}")
        print(f"  Backtracks A-B-A: {demo['backtracks']}")
        print(f"  Motivo de finalización: {demo['finish_reason']}")
        print(f"  Informe de misión: {demo['mission_report_file']}")

        if demo.get("last_victim_location"):
            location = demo["last_victim_location"]
            print(f"  Última víctima localizada: ({location['x']}, {location['y']})")

    print("\nArchivos demo generados:")
    print(f"- {output_dir / 'unity_demo_manifest.json'}")
    print(f"- {output_dir / 'mission_reports_index.md'}")

    for demo in manifest_demos:
        print(f"- {output_dir / demo['trajectory_file']}")
        print(f"- {output_dir / demo['world_file']}")
        print(f"- {output_dir / demo['mission_report_file']}")

    if unity_streaming_assets is not None:
        print("\nArchivos copiados a Unity:")
        print(f"- {unity_streaming_assets}")

    print("\nPara probar en Unity:")

    for demo in manifest_demos:
        print(f"\nDemo {demo['demo']:03d}:")
        print(
            "  MissionReplayController → Mission File Name = "
            f"{demo['trajectory_file']}"
        )
        print(
            "  MissionMapBuilder       → World File Name   = "
            f"{demo['world_file']}"
        )

    print("\nInformes generados:")
    for demo in manifest_demos:
        print(f"  - {output_dir / demo['mission_report_file']}")

    print("\nTeclas en Unity:")
    print("  1 → Demo víctima/riesgo")
    print("  2 → Demo retorno a base")
    print("  R → Reiniciar demo actual")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera dos escenarios demo para Unity y sus informes de misión."
    )

    parser.add_argument(
        "--candidates",
        type=int,
        default=120,
        help="Cantidad de misiones candidatas a generar.",
    )

    parser.add_argument(
        "--selected",
        type=int,
        default=2,
        help="Cantidad de demos seleccionadas. Para esta versión se fuerza a 2.",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=180,
        help="Cantidad máxima de pasos por misión.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=1600,
        help="Seed base para generar mundos reproducibles.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Carpeta donde se guardan los escenarios demo.",
    )

    parser.add_argument(
        "--q-table-path",
        type=Path,
        default=DEFAULT_Q_TABLE_PATH,
        help="Ruta de la Q-table entrenada.",
    )

    parser.add_argument(
        "--unity-dir",
        type=Path,
        default=DEFAULT_UNITY_DIR,
        help="Ruta del proyecto Unity.",
    )

    parser.add_argument(
        "--no-unity-copy",
        action="store_true",
        help="No copiar archivos a Assets/StreamingAssets.",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="No imprimir logs detallados de cada misión.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_dir = args.output_dir
    q_table_path = args.q_table_path
    unity_dir = args.unity_dir

    selected_count = 2

    clean_output_dir(output_dir)

    report = generate_candidates(
        output_dir=output_dir,
        q_table_path=q_table_path,
        candidates=args.candidates,
        max_steps=args.max_steps,
        seed=args.seed,
        quiet=args.quiet,
    )

    candidates = build_candidate_table(report)

    if not candidates:
        raise RuntimeError("No se generaron candidatos para seleccionar demos.")

    selected = select_two_scenarios(candidates)

    if len(selected) < selected_count:
        raise RuntimeError(
            "No se pudieron seleccionar dos escenarios demo. "
            "Probá aumentando --candidates."
        )

    manifest_demos = copy_selected_files(selected, output_dir)

    unity_streaming_assets = None

    if not args.no_unity_copy:
        unity_streaming_assets = copy_to_unity_streaming_assets(
            output_dir=output_dir,
            unity_dir=unity_dir,
            manifest_demos=manifest_demos,
        )

    print_summary(
        candidates=candidates,
        manifest_demos=manifest_demos,
        output_dir=output_dir,
        unity_streaming_assets=unity_streaming_assets,
    )


if __name__ == "__main__":
    main()