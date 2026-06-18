import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_trajectory(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def plot_trajectory(trajectory, mission_number: int, output_path: Path):
    xs = [point["x"] for point in trajectory]
    ys = [point["y"] for point in trajectory]
    actions = [point["action"] for point in trajectory]

    plt.figure(figsize=(8, 8))

    plt.plot(xs, ys, marker="o", linewidth=1)
    plt.scatter(xs[0], ys[0], s=120, label="Inicio")
    plt.scatter(xs[-1], ys[-1], s=120, label="Fin")

    for index, point in enumerate(trajectory):
        if index % 5 == 0:
            plt.text(
                point["x"] + 0.1,
                point["y"] + 0.1,
                str(point["step"]),
                fontsize=8
            )

    plt.title(f"Trayectoria misión autónoma {mission_number}")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.xlim(-1, 20)
    plt.ylim(20, -1)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.show()

    print(f"Imagen generada en: {output_path}")
    print()
    print("Últimas acciones:")
    for point, action in zip(trajectory[-10:], actions[-10:]):
        print(
            f"Paso {point['step']:03d} | "
            f"pos=({point['x']}, {point['y']}) | "
            f"acción={action}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Visualiza la trayectoria de una misión autónoma RescueTwin."
    )
    parser.add_argument(
        "--mission",
        type=int,
        required=True,
        help="Número de misión a visualizar. Ejemplo: 19"
    )
    parser.add_argument(
        "--reports-dir",
        default="reports/autonomous_missions",
        help="Carpeta donde están los reportes de misiones."
    )

    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    trajectory_path = reports_dir / f"mission_{args.mission:03d}_trajectory.json"
    output_path = reports_dir / f"mission_{args.mission:03d}_trajectory.png"

    trajectory = load_trajectory(trajectory_path)
    plot_trajectory(trajectory, args.mission, output_path)


if __name__ == "__main__":
    main()