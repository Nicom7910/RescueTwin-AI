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
    files = sorted(LOG_DIR.glob("ros_mission_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
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

    # Zonas lógicas alineadas con el mundo Gazebo.
    zones = [
        ("Entrada", -3.0, 0.0),
        ("Escombros", 1.5, 0.8),
        ("Riesgo medio", 3.0, -2.8),
        ("Riesgo alto", 5.0, 2.8),
        ("Víctima probable", 7.0, 2.6),
    ]

    plt.figure(figsize=(11, 7))

    # Ruta del robot.
    plt.plot(df["x"], df["y"], marker="o", linewidth=2, label="Ruta del robot")

    # Inicio y fin.
    plt.scatter(df["x"].iloc[0], df["y"].iloc[0], s=140, marker="s", label="Inicio")
    plt.scatter(df["x"].iloc[-1], df["y"].iloc[-1], s=160, marker="*", label="Fin")

    # Zonas.
    for name, x, y in zones:
        plt.scatter([x], [y], s=120)
        plt.text(x + 0.1, y + 0.1, name)

    # Marcar puntos con riesgo alto o víctima.
    if "risk_level" in df.columns:
        high = df[df["risk_level"] == "Alto"]
        if not high.empty:
            plt.scatter(high["x"], high["y"], s=220, facecolors="none", edgecolors="red", linewidths=2, label="Riesgo alto")

    if "person_detected" in df.columns:
        victim = df[df["person_detected"] == 1]
        if not victim.empty:
            plt.scatter(victim["x"], victim["y"], s=260, facecolors="none", edgecolors="green", linewidths=2, label="Persona detectada")

    plt.title("RescueTwin AI - Ruta 2D de misión")
    plt.xlabel("Posición X")
    plt.ylabel("Posición Y")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)

    print(f"CSV usado: {csv_path}")
    print(f"Imagen generada: {output_path}")


if __name__ == "__main__":
    main()
