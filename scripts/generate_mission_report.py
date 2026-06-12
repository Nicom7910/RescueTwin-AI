#!/usr/bin/env python3

"""
Generador de reporte de misión RescueTwin AI.

Toma el último CSV de misión y el entorno aleatorio generado.
Produce un reporte en Markdown dentro de reports/mission_logs.
"""

import json
import math
import sys
from datetime import datetime
from pathlib import Path

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


def calculate_distance(df, x_col, y_col):
    distance = 0.0

    for i in range(1, len(df)):
        x1 = df[x_col].iloc[i - 1]
        y1 = df[y_col].iloc[i - 1]
        x2 = df[x_col].iloc[i]
        y2 = df[y_col].iloc[i]

        distance += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    return distance


def main():
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = find_latest_csv()

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError(f"El CSV está vacío: {csv_path}")

    environment = load_environment()

    x_col = find_column(df, ["x", "pos_x", "robot_x"])
    y_col = find_column(df, ["y", "pos_y", "robot_y"])

    if x_col is None or y_col is None:
        raise ValueError("No se encontraron columnas de posición x/y en el CSV.")

    state_series = get_series_or_default(df, ["mission_state", "state", "estado"], "")
    person_series = get_series_or_default(df, ["person_detected", "persona"], 0)
    signal_series = get_series_or_default(df, ["victim_signal", "senal_victima"], 0)
    risk_series = get_series_or_default(df, ["risk_level", "risk", "riesgo_local"], "Desconocido")
    battery_series = get_series_or_default(df, ["battery", "bateria"], None)
    explored_series = get_series_or_default(df, ["explorado", "exploration_percent"], None)

    total_distance = calculate_distance(df, x_col, y_col)

    final_state = str(state_series.iloc[-1]) if len(state_series) else "SIN_ESTADO"

    try:
        victim_detected = pd.to_numeric(person_series, errors="coerce").fillna(0).max() == 1
    except Exception:
        victim_detected = False

    try:
        max_signal = pd.to_numeric(signal_series, errors="coerce").fillna(0).max()
    except Exception:
        max_signal = 0.0

    try:
        final_battery = pd.to_numeric(battery_series, errors="coerce").dropna().iloc[-1]
    except Exception:
        final_battery = None

    try:
        final_explored = pd.to_numeric(explored_series, errors="coerce").dropna().iloc[-1]
    except Exception:
        final_explored = None

    risk_counts = risk_series.astype(str).value_counts().to_dict()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = LOG_DIR / f"mission_report_{timestamp}.md"

    lines = []

    lines.append("# Reporte de misión - RescueTwin AI")
    lines.append("")
    lines.append(f"**Archivo CSV analizado:** `{csv_path.name}`")
    lines.append(f"**Fecha de generación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    lines.append("")

    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(f"- Estado final de la misión: **{final_state}**")
    lines.append(f"- Distancia recorrida estimada: **{total_distance:.2f} unidades**")
    lines.append(f"- Cantidad de registros analizados: **{len(df)}**")
    lines.append(f"- Víctima detectada: **{'Sí' if victim_detected else 'No'}**")
    lines.append(f"- Señal máxima de víctima: **{max_signal:.2f}**")

    if final_battery is not None:
        lines.append(f"- Batería final estimada: **{final_battery:.1f}%**")

    if final_explored is not None:
        lines.append(f"- Porcentaje estimado de exploración: **{final_explored:.1f}%**")

    lines.append("")

    lines.append("## 2. Entorno simulado")
    lines.append("")

    if environment:
        lines.append(
            "El entorno fue generado aleatoriamente al inicio de la ejecución. "
            "Esto simula un escenario de rescate donde el robot no conoce de antemano "
            "la ubicación exacta de escombros, obstáculos, zonas peligrosas o víctimas."
        )
        lines.append("")
        lines.append(f"- Seed de simulación: **{environment.get('seed', 'N/D')}**")
        lines.append(f"- Obstáculos generados: **{len(environment.get('obstacles', []))}**")
        lines.append(f"- Zonas de riesgo generadas: **{len(environment.get('risk_zones', []))}**")

        victim = environment.get("victim", {})

        if victim:
            lines.append(
                f"- Ubicación real de víctima probable: "
                f"**x={victim.get('x')}, y={victim.get('y')}**"
            )

        lines.append("")
        lines.append("### Obstáculos generados")
        lines.append("")

        for obstacle in environment.get("obstacles", []):
            lines.append(
                f"- {obstacle.get('name')} | tipo={obstacle.get('type')} | "
                f"x={obstacle.get('x')}, y={obstacle.get('y')}, "
                f"radio={obstacle.get('radius')}"
            )

        lines.append("")
        lines.append("### Zonas de riesgo generadas")
        lines.append("")

        for zone in environment.get("risk_zones", []):
            lines.append(
                f"- {zone.get('name')} | nivel={zone.get('risk_level')} | "
                f"x={zone.get('x')}, y={zone.get('y')}, "
                f"radio={zone.get('radius')}"
            )
    else:
        lines.append("No se encontró archivo `latest_environment.json`.")
        lines.append("")

    lines.append("")
    lines.append("## 3. Riesgos detectados")
    lines.append("")

    if risk_counts:
        for risk, count in risk_counts.items():
            lines.append(f"- {risk}: **{count} registros**")
    else:
        lines.append("- No se encontraron datos de riesgo.")

    lines.append("")
    lines.append("## 4. Interpretación")
    lines.append("")

    if victim_detected:
        lines.append(
            "El robot logró detectar una víctima probable durante la exploración. "
            "Al detectar la señal, priorizó la aproximación controlada, se detuvo y "
            "generó una alerta para la base."
        )
    elif max_signal > 0.35:
        lines.append(
            "El robot detectó señal parcial de víctima, pero no llegó a confirmar "
            "detección directa dentro del radio definido. Se recomienda extender "
            "la duración de la misión o permitir mayor exploración de sectores."
        )
    else:
        lines.append(
            "El robot completó parte de la exploración sin detectar una víctima. "
            "Esto puede deberse a que la víctima quedó fuera de los sectores explorados "
            "durante el tiempo de simulación o a la presencia de obstáculos/riesgos."
        )

    lines.append("")
    lines.append(
        "La misión utiliza obstáculos y zonas de riesgo generadas aleatoriamente. "
        "Por eso, cada ejecución puede producir una ruta distinta y un resultado distinto, "
        "lo cual representa mejor la incertidumbre de un escenario real de rescate."
    )

    lines.append("")
    lines.append("## 5. Conclusión")
    lines.append("")
    lines.append(
        "RescueTwin AI permite simular el comportamiento de un robot cuadrúpedo "
        "en escenarios de rescate con incertidumbre. El sistema integra sensores "
        "simulados, análisis de riesgo, toma de decisiones autónoma, registro de misión "
        "y visualización del recorrido. La generación aleatoria del entorno mejora "
        "el realismo de la simulación porque evita que el robot dependa de un mapa "
        "predefinido y obliga al sistema a reaccionar ante eventos detectados durante "
        "la exploración."
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Reporte generado: {output_path}")


if __name__ == "__main__":
    main()