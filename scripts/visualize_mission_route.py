#!/usr/bin/env python3

"""
Visualización 2D de ruta RescueTwin AI.

Uso:
    python3 scripts/visualize_mission_route.py

O indicando un CSV:
    python3 scripts/visualize_mission_route.py reports/mission_logs/ros_mission_YYYYMMDD_HHMMSS.csv

Genera:
    reports/mission_logs/mission_route_YYYYMMDD_HHMMSS.png
"""

from pathlib import Path
import sys
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt


PROJECT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_DIR / "reports" / "mission_logs"


def find_latest_csv() -> Path:
    files = sorted(
        LOG_DIR.glob("ros_mission_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(f"No se encontraron CSV de misión en {LOG_DIR}")

    return files[0]


def main():
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = find_latest_csv()

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError(f"El archivo está vacío: {csv_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = LOG_DIR / f"mission_route_{timestamp}.png"

    zones = [
        ("Entrada", -3.0, 0.0),
        ("Escombros", 1.5, 0.8),
        ("Riesgo medio", 3.0, -2.8),
        ("Riesgo alto", 5.0, 2.8),
        ("Víctima probable", 6.8, 2.6),
    ]

    planned_route = [
        (-3.0, 0.0),
        (-1.2, 0.2),
        (1.3, 0.8),
        (2.4, 0.3),
        (3.5, 1.2),
        (4.7, 2.0),
        (5.7, 2.2),
        (6.8, 2.6),
    ]

    plt.figure(figsize=(12, 7))

    # Ruta planificada.
    planned_x = [p[0] for p in planned_route]
    planned_y = [p[1] for p in planned_route]
    plt.plot(
        planned_x,
        planned_y,
        linestyle="--",
        linewidth=1.5,
        alpha=0.6,
        label="Ruta planificada",
    )

    # Ruta real del robot.
    plt.plot(
        df["x"],
        df["y"],
        marker="o",
        markersize=4,
        linewidth=2,
        label="Ruta real del robot",
    )

    # Inicio y fin.
    plt.scatter(df["x"].iloc[0], df["y"].iloc[0], s=150, marker="s", label="Inicio")
    plt.scatter(df["x"].iloc[-1], df["y"].iloc[-1], s=180, marker="*", label="Fin")

    # Zonas de referencia.
    for name, x, y in zones:
        plt.scatter([x], [y], s=130)
        plt.text(x + 0.1, y + 0.1, name, fontsize=10)

    # Riesgo alto.
    if "risk_level" in df.columns:
        high = df[df["risk_level"].astype(str).str.lower() == "alto"]

        if not high.empty:
            plt.scatter(
                high["x"],
                high["y"],
                s=180,
                facecolors="none",
                edgecolors="red",
                linewidths=2,
                label="Puntos con riesgo alto",
            )

    # Estados de evasión.
    if "mission_state" in df.columns:
        evasion = df[
            df["mission_state"].astype(str).str.contains(
                "RODEANDO|EVITANDO",
                case=False,
                na=False,
            )
        ]

        if not evasion.empty:
            plt.scatter(
                evasion["x"],
                evasion["y"],
                s=90,
                marker="x",
                label="Maniobras evasivas",
            )

    # Persona detectada.
    if "person_detected" in df.columns:
        victim = df[df["person_detected"] == 1]

        if not victim.empty:
            plt.scatter(
                victim["x"],
                victim["y"],
                s=280,
                facecolors="none",
                edgecolors="green",
                linewidths=2.5,
                label="Víctima detectada",
            )

    # Último estado.
    final_state = "SIN_ESTADO"
    if "mission_state" in df.columns:
        final_state = str(df["mission_state"].iloc[-1])

    plt.title(f"RescueTwin AI - Ruta 2D de misión | Estado final: {final_state}")
    plt.xlabel("Posición X")
    plt.ylabel("Posición Y")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.axis("equal")
    plt.tight_layout()

    plt.savefig(output_path, dpi=160)

    print(f"CSV usado: {csv_path}")
    print(f"Imagen generada: {output_path}")
    print(f"Estado final: {final_state}")


if __name__ == "__main__":
    main()