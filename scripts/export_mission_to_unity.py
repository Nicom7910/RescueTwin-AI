import argparse
import json
import shutil
from pathlib import Path
from typing import List, Dict


DEFAULT_MISSIONS_DIR = Path("reports/autonomous_missions")
DEFAULT_UNITY_DIR = Path("unity/RescueTwinUnity_v2")


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def smooth_trajectory_for_unity(trajectory: List[Dict]) -> List[Dict]:
    """
    Limpia micro-bucles visuales del tipo A-B-A.

    No modifica la misión original.
    Solo genera una versión más clara para Unity.
    """

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


def build_report(
    output_path: Path,
    mission_number: int,
    trajectory: List[Dict],
    world: Dict,
    smoothed: bool,
) -> None:
    victims_found = sum(1 for step in trajectory if step.get("victim_found") is True)
    victim_search_steps = sum(1 for step in trajectory if step.get("victim_search_mode") is True)
    return_steps = sum(1 for step in trajectory if step.get("return_to_base_mode") is True)
    risk_steps = sum(1 for step in trajectory if step.get("risk_level") in {"MEDIO", "ALTO"})

    obstacles = world.get("obstacles", [])
    victims = world.get("victims", [])
    risk_cells = world.get("risk_cells", [])

    lines = []

    lines.append(f"# Informe de misión exportada a Unity - Misión {mission_number:03d}")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---|---:|")
    lines.append(f"| Misión | {mission_number:03d} |")
    lines.append(f"| Pasos visualizados | {len(trajectory)} |")
    lines.append(f"| Trayectoria suavizada | {'Sí' if smoothed else 'No'} |")
    lines.append(f"| Víctimas encontradas | {victims_found} |")
    lines.append(f"| Pasos en búsqueda de víctima | {victim_search_steps} |")
    lines.append(f"| Pasos en retorno a base | {return_steps} |")
    lines.append(f"| Pasos con riesgo medio/alto | {risk_steps} |")
    lines.append(f"| Obstáculos del mundo | {len(obstacles)} |")
    lines.append(f"| Víctimas iniciales del mundo | {len(victims)} |")
    lines.append(f"| Celdas de riesgo del mundo | {len(risk_cells)} |")
    lines.append("")

    lines.append("## Decisiones paso a paso")
    lines.append("")
    lines.append("| Paso | Posición | Acción | Riesgo | Batería | Modo | Víctima detectada | Víctima localizada |")
    lines.append("|---:|---:|---|---|---|---|---|---|")

    for step in trajectory:
        mode = "EXPLORACIÓN"

        if step.get("return_to_base_mode") is True:
            mode = "RETORNO A BASE"
        elif step.get("victim_search_mode") is True:
            mode = "BÚSQUEDA DE VÍCTIMA"

        lines.append(
            f"| {step.get('step')} "
            f"| ({step.get('x')}, {step.get('y')}) "
            f"| {step.get('action', '-')} "
            f"| {step.get('risk_level', '-')} "
            f"| {step.get('battery_level', '-')} "
            f"| {mode} "
            f"| {'Sí' if step.get('victim_detected') else 'No'} "
            f"| {'Sí' if step.get('victim_found') else 'No'} |"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_mission(
    mission_number: int,
    missions_dir: Path,
    unity_dir: Path,
    output_prefix: str,
    smooth: bool,
    generate_report: bool,
) -> None:
    mission_id = f"mission_{mission_number:03d}"

    source_trajectory = missions_dir / f"{mission_id}_trajectory.json"
    source_world = missions_dir / f"{mission_id}_world.json"

    if not source_trajectory.exists():
        raise FileNotFoundError(f"No existe la trayectoria: {source_trajectory}")

    if not source_world.exists():
        raise FileNotFoundError(f"No existe el mundo: {source_world}")

    streaming_assets_dir = unity_dir / "Assets" / "StreamingAssets"
    streaming_assets_dir.mkdir(parents=True, exist_ok=True)

    target_trajectory = streaming_assets_dir / f"{output_prefix}_{mission_number:03d}_trajectory.json"
    target_world = streaming_assets_dir / f"{output_prefix}_{mission_number:03d}_world.json"

    trajectory = load_json(source_trajectory)
    world = load_json(source_world)

    if not isinstance(trajectory, list):
        raise ValueError(f"La trayectoria no tiene formato de lista: {source_trajectory}")

    if smooth:
        trajectory_to_export = smooth_trajectory_for_unity(trajectory)
    else:
        trajectory_to_export = trajectory

    target_trajectory.write_text(
        json.dumps(trajectory_to_export, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    shutil.copy2(source_world, target_world)

    report_path = None

    if generate_report:
        report_path = missions_dir / f"{output_prefix}_{mission_number:03d}_mission_report.md"
        build_report(
            output_path=report_path,
            mission_number=mission_number,
            trajectory=trajectory_to_export,
            world=world,
            smoothed=smooth,
        )

    print("\nMisión exportada correctamente a Unity")
    print("-" * 72)
    print(f"Trayectoria: {target_trajectory}")
    print(f"Mundo:       {target_world}")

    if report_path is not None:
        print(f"Informe:    {report_path}")

    print("\nConfiguración en Unity:")
    print(f"MissionReplayController → Mission File Name = {target_trajectory.name}")
    print(f"MissionMapBuilder       → World File Name   = {target_world.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta una misión cualquiera a Unity para visualizarla."
    )

    parser.add_argument(
        "mission_number",
        type=int,
        help="Número de misión a exportar. Ejemplo: 15 para mission_015.",
    )

    parser.add_argument(
        "--missions-dir",
        type=Path,
        default=DEFAULT_MISSIONS_DIR,
        help="Carpeta donde están las misiones generadas.",
    )

    parser.add_argument(
        "--unity-dir",
        type=Path,
        default=DEFAULT_UNITY_DIR,
        help="Ruta del proyecto Unity.",
    )

    parser.add_argument(
        "--output-prefix",
        type=str,
        default="custom_mission",
        help="Prefijo del archivo exportado a Unity.",
    )

    parser.add_argument(
        "--no-smooth",
        action="store_true",
        help="Exporta la trayectoria original sin suavizar.",
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="No genera informe markdown de la misión.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    export_mission(
        mission_number=args.mission_number,
        missions_dir=args.missions_dir,
        unity_dir=args.unity_dir,
        output_prefix=args.output_prefix,
        smooth=not args.no_smooth,
        generate_report=not args.no_report,
    )


if __name__ == "__main__":
    main()