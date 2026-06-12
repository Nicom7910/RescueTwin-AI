#!/usr/bin/env python3

"""
Visualización 2D de misión RescueTwin AI.

Genera:
- Ruta real del robot.
- Obstáculos aleatorios.
- Zonas de riesgo aleatorias.
- Víctima probable.
- Puntos con maniobras evasivas.
- Puntos con detección de víctima.
- Estado final de misión.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


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


def load_environment():
    env_path = LOG_DIR / "latest_environment.json"

    if not env_path.exists():
        return None

    with open(env_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col

    return None


def get_series_or_default(df, candidates, default):
    col = find_column(df, candidates)

    if col is None:
        return pd.Series([default] * len(df))

    return df[col]


def main():
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = find_latest_csv()

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError(f"El CSV está vacío: {csv_path}")

    x_col = find_column(df, ["x", "pos_x", "robot_x"])
    y_col = find_column(df, ["y", "pos_y", "robot_y"])

    if x_col is None or y_col is None:
        raise ValueError(
            "No se encontraron columnas de posición. "
            "Se esperaban columnas x/y, pos_x/pos_y o robot_x/robot_y."
        )

    environment = load_environment()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = LOG_DIR / f"mission_route_{timestamp}.png"

    plt.figure(figsize=(13, 8))

    # Entorno aleatorio.
    if environment:
        bounds = environment.get("map_bounds", {})
        x_min = bounds.get("x_min", -3.5)
        x_max = bounds.get("x_max", 7.4)
        y_min = bounds.get("y_min", -3.2)
        y_max = bounds.get("y_max", 3.2)

        # Obstáculos.
        for obstacle in environment.get("obstacles", []):
            circle = plt.Circle(
                (obstacle["x"], obstacle["y"]),
                obstacle["radius"],
                fill=False,
                linewidth=1.7,
                linestyle="-",
            )
            plt.gca().add_patch(circle)

            plt.text(
                obstacle["x"] + 0.08,
                obstacle["y"] + 0.08,
                "Obstáculo",
                fontsize=8,
            )

        # Zonas de riesgo.
        for zone in environment.get("risk_zones", []):
            circle = plt.Circle(
                (zone["x"], zone["y"]),
                zone["radius"],
                fill=False,
                linewidth=2,
                linestyle="--",
            )
            plt.gca().add_patch(circle)

            plt.text(
                zone["x"] + 0.08,
                zone["y"] + 0.08,
                f"Riesgo {zone['risk_level']}",
                fontsize=8,
            )

        # Entrada.
        entry = environment.get("entry", {})
        if entry:
            plt.scatter(entry["x"], entry["y"], s=170, marker="s", label="Entrada")

        # Víctima probable.
        victim = environment.get("victim", {})
        if victim:
            plt.scatter(
                victim["x"],
                victim["y"],
                s=220,
                marker="*",
                label="Víctima probable real",
            )

            signal_circle = plt.Circle(
                (victim["x"], victim["y"]),
                victim.get("signal_radius", 3.2),
                fill=False,
                linestyle=":",
                linewidth=1.2,
            )
            plt.gca().add_patch(signal_circle)

            plt.text(
                victim["x"] + 0.1,
                victim["y"] + 0.1,
                "Víctima probable",
                fontsize=10,
            )
    else:
        x_min, x_max = -3.5, 7.4
        y_min, y_max = -3.2, 3.2

    # Ruta real.
    plt.plot(
        df[x_col],
        df[y_col],
        marker="o",
        markersize=4,
        linewidth=2,
        label="Ruta real del robot",
    )

    # Inicio y fin.
    plt.scatter(
        df[x_col].iloc[0],
        df[y_col].iloc[0],
        s=160,
        marker="s",
        label="Inicio registrado",
    )

    plt.scatter(
        df[x_col].iloc[-1],
        df[y_col].iloc[-1],
        s=200,
        marker="X",
        label="Fin registrado",
    )

    # Estados.
    state_series = get_series_or_default(
        df,
        ["mission_state", "state", "estado"],
        "",
    ).astype(str)

    evasion_mask = state_series.str.contains(
        "EVITANDO|RODEANDO",
        case=False,
        na=False,
    )

    if evasion_mask.any():
        plt.scatter(
            df.loc[evasion_mask, x_col],
            df.loc[evasion_mask, y_col],
            s=90,
            marker="x",
            label="Maniobras evasivas",
        )

    signal_series = get_series_or_default(
        df,
        ["victim_signal", "senal_victima"],
        0,
    )

    try:
        signal_values = pd.to_numeric(signal_series, errors="coerce").fillna(0)
        signal_mask = signal_values > 0.35

        if signal_mask.any():
            plt.scatter(
                df.loc[signal_mask, x_col],
                df.loc[signal_mask, y_col],
                s=95,
                marker="^",
                label="Señal de víctima detectada",
            )
    except Exception:
        pass

    person_series = get_series_or_default(
        df,
        ["person_detected", "persona", "victima_detectada"],
        0,
    )

    try:
        person_values = pd.to_numeric(person_series, errors="coerce").fillna(0)
        person_mask = person_values == 1

        if person_mask.any():
            plt.scatter(
                df.loc[person_mask, x_col],
                df.loc[person_mask, y_col],
                s=300,
                facecolors="none",
                edgecolors="green",
                linewidths=2.5,
                label="Víctima detectada",
            )
    except Exception:
        pass

    final_state = "SIN_ESTADO"

    if len(state_series) > 0:
        final_state = str(state_series.iloc[-1])

    explored_series = get_series_or_default(
        df,
        ["explorado", "exploration_percent", "porcentaje_explorado"],
        None,
    )

    explored_text = ""

    try:
        explored_values = pd.to_numeric(explored_series, errors="coerce").dropna()

        if not explored_values.empty:
            explored_text = f" | Exploración estimada: {explored_values.iloc[-1]:.1f}%"
    except Exception:
        explored_text = ""

    plt.title(
        f"RescueTwin AI - Ruta 2D de misión | Estado final: {final_state}{explored_text}"
    )

    plt.xlabel("Posición X")
    plt.ylabel("Posición Y")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")
    plt.xlim(x_min - 0.4, x_max + 0.4)
    plt.ylim(y_min - 0.4, y_max + 0.4)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.tight_layout()

    plt.savefig(output_path, dpi=160)

    print(f"CSV usado: {csv_path}")
    print(f"Imagen generada: {output_path}")
    print(f"Estado final: {final_state}")


if __name__ == "__main__":
    main()