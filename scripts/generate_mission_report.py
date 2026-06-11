#!/usr/bin/env python3
"""
generate_mission_report.py

Generador automático de reporte de misión para RescueTwin AI.

Este script lee la última bitácora CSV generada por `mission_logger_node.py`
en `reports/mission_logs/` y genera un reporte completo con:

- Resumen ejecutivo de la misión.
- Métricas principales.
- Riesgo máximo detectado.
- Cantidad de alertas.
- Estado final.
- Sensores finales.
- Gráficos de evolución temporal.
- Visualización 2D de la ruta.
- Archivo Markdown final listo para incluir en el proyecto.

Uso desde la raíz del proyecto:

    python3 scripts/generate_mission_report.py

Uso indicando un CSV específico:

    python3 scripts/generate_mission_report.py reports/mission_logs/ros_mission_YYYYMMDD_HHMMSS.csv

Opciones:

    python3 scripts/generate_mission_report.py --show
    python3 scripts/generate_mission_report.py --output-name reporte_mision_demo

Salidas generadas en:

    reports/mission_reports/
    reports/mission_logs/

Requisitos:

    pip install pandas matplotlib
"""

from __future__ import annotations

import argparse
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


PROJECT_DIR = Path(__file__).resolve().parents[1]
MISSION_LOG_DIR = PROJECT_DIR / "reports" / "mission_logs"
REPORT_DIR = PROJECT_DIR / "reports" / "mission_reports"
FIGURES_DIR = REPORT_DIR / "figures"


# ============================================================
# Utilidades
# ============================================================

def print_step(text: str) -> None:
    print(f"[+] {text}")


def ensure_dirs() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def find_latest_csv() -> Path:
    """
    Busca el CSV más reciente de misión.

    Prioriza archivos generados por mission_logger_node:
        ros_mission_*.csv

    También acepta otros CSV de misión:
        mission_*.csv
        mission_realistic_*.csv
    """
    patterns = [
        "ros_mission_*.csv",
        "mission_realistic_*.csv",
        "mission_*.csv",
    ]

    candidates = []
    for pattern in patterns:
        candidates.extend(MISSION_LOG_DIR.glob(pattern))

    candidates = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)

    if not candidates:
        raise FileNotFoundError(
            f"No se encontraron CSV de misión en {MISSION_LOG_DIR}. "
            "Primero ejecutá run_rescuetwin_full_project.py o mission_logger_node.py."
        )

    return candidates[0]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza columnas para soportar distintos nombres generados
    por diferentes versiones de la bitácora.
    """
    df = df.copy()

    aliases = {
        "risk": "risk_level",
        "nivel_riesgo": "risk_level",
        "accion": "recommended_action",
        "action_ai": "recommended_action",
        "temperature": "temperature",
        "temperatura": "temperature",
        "gas": "gas_ppm",
        "vibration": "vibration",
        "vibracion": "vibration",
        "inclination": "inclination",
        "inclinacion": "inclination",
        "battery": "battery",
        "bateria": "battery",
        "obstacle": "obstacle_distance",
        "distancia_obstaculo": "obstacle_distance",
        "person": "person_detected",
        "persona_detectada": "person_detected",
        "state": "mission_state",
        "decision": "decision_status",
    }

    for source, target in aliases.items():
        if source in df.columns and target not in df.columns:
            df[target] = df[source]

    # Asegurar columnas mínimas.
    default_columns = {
        "timestamp": "",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "mission_state": "SIN_ESTADO",
        "risk_level": "Desconocido",
        "recommended_action": "",
        "temperature": 0.0,
        "gas_ppm": 0.0,
        "vibration": 0.0,
        "inclination": 0.0,
        "battery": 0.0,
        "obstacle_distance": 0.0,
        "person_detected": 0,
        "current_objective": "",
        "decision_status": "",
        "last_alert": "SIN_ALERTAS",
    }

    for col, default in default_columns.items():
        if col not in df.columns:
            df[col] = default

    numeric_cols = [
        "x",
        "y",
        "z",
        "temperature",
        "gas_ppm",
        "vibration",
        "inclination",
        "battery",
        "obstacle_distance",
        "person_detected",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["risk_level"] = df["risk_level"].fillna("Desconocido").astype(str)
    df["mission_state"] = df["mission_state"].fillna("SIN_ESTADO").astype(str)
    df["recommended_action"] = df["recommended_action"].fillna("").astype(str)
    df["current_objective"] = df["current_objective"].fillna("").astype(str)
    df["decision_status"] = df["decision_status"].fillna("").astype(str)
    df["last_alert"] = df["last_alert"].fillna("SIN_ALERTAS").astype(str)

    return df


def clean_text(text: str, max_len: int = 180) -> str:
    text = str(text).replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def estimate_distance(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0

    distance = 0.0
    points = df[["x", "y"]].to_numpy()

    for i in range(1, len(points)):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        distance += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    return float(distance)


def risk_priority(risk: str) -> int:
    return {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3,
        "Desconocido": 0,
    }.get(str(risk), 0)


def get_max_risk(df: pd.DataFrame) -> str:
    if df.empty:
        return "Desconocido"
    return max(df["risk_level"].astype(str), key=risk_priority)


def count_alerts(df: pd.DataFrame) -> int:
    if "last_alert" not in df.columns:
        return 0

    alerts = df["last_alert"].astype(str)
    alerts = alerts[~alerts.str.contains("SIN_ALERTAS", case=False, na=False)]
    alerts = alerts[alerts.str.strip() != ""]
    return int(alerts.nunique())


def get_unique_alerts(df: pd.DataFrame) -> list[str]:
    if "last_alert" not in df.columns:
        return []

    alerts = df["last_alert"].astype(str)
    alerts = alerts[~alerts.str.contains("SIN_ALERTAS", case=False, na=False)]
    alerts = alerts[alerts.str.strip() != ""]
    return [clean_text(alert, max_len=300) for alert in alerts.drop_duplicates().tolist()]


# ============================================================
# Gráficos
# ============================================================

def plot_route(df: pd.DataFrame, output_name: str, show: bool = False) -> Path:
    output_path = FIGURES_DIR / f"{output_name}_ruta_2d.png"

    zones = [
        ("Entrada", -3.0, 0.0),
        ("Escombros", 1.5, 0.8),
        ("Riesgo medio", 3.0, -2.8),
        ("Riesgo alto", 5.0, 2.8),
        ("Víctima probable", 7.0, 2.6),
    ]

    plt.figure(figsize=(11, 7))

    plt.plot(df["x"], df["y"], marker="o", linewidth=2, label="Ruta del robot")

    if not df.empty:
        plt.scatter(df["x"].iloc[0], df["y"].iloc[0], s=140, marker="s", label="Inicio")
        plt.scatter(df["x"].iloc[-1], df["y"].iloc[-1], s=180, marker="*", label="Fin")

    for name, x, y in zones:
        plt.scatter([x], [y], s=120)
        plt.text(x + 0.1, y + 0.1, name)

    high = df[df["risk_level"] == "Alto"]
    if not high.empty:
        plt.scatter(
            high["x"],
            high["y"],
            s=220,
            facecolors="none",
            edgecolors="red",
            linewidths=2,
            label="Riesgo alto",
        )

    victim = df[df["person_detected"] == 1]
    if not victim.empty:
        plt.scatter(
            victim["x"],
            victim["y"],
            s=260,
            facecolors="none",
            edgecolors="green",
            linewidths=2,
            label="Persona detectada",
        )

    plt.title("RescueTwin AI - Ruta 2D de misión")
    plt.xlabel("Posición X")
    plt.ylabel("Posición Y")
    plt.grid(True, alpha=0.3)
    plt.axis("equal")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)

    if show:
        plt.show()
    else:
        plt.close()

    return output_path


def plot_sensor_series(df: pd.DataFrame, output_name: str, show: bool = False) -> list[Path]:
    plots = []

    series_to_plot = [
        ("gas_ppm", "Evolución de gas detectado", "Gas ppm"),
        ("temperature", "Evolución de temperatura", "Temperatura"),
        ("vibration", "Evolución de vibración", "Vibración"),
        ("inclination", "Evolución de inclinación", "Inclinación"),
        ("battery", "Evolución de batería", "Batería (%)"),
        ("obstacle_distance", "Evolución de distancia a obstáculos", "Distancia a obstáculo"),
    ]

    df_plot = df.reset_index(drop=True).copy()
    df_plot["step"] = range(1, len(df_plot) + 1)

    for col, title, ylabel in series_to_plot:
        if col not in df_plot.columns:
            continue

        output_path = FIGURES_DIR / f"{output_name}_{col}.png"

        plt.figure(figsize=(10, 5))
        plt.plot(df_plot["step"], df_plot[col], marker="o", linewidth=2)
        plt.title(title)
        plt.xlabel("Paso de misión")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=160)

        if show:
            plt.show()
        else:
            plt.close()

        plots.append(output_path)

    return plots


def plot_risk_counts(df: pd.DataFrame, output_name: str, show: bool = False) -> Path:
    output_path = FIGURES_DIR / f"{output_name}_riesgos.png"

    order = ["Bajo", "Medio", "Alto", "Desconocido"]
    counts = df["risk_level"].value_counts()
    counts = counts.reindex([r for r in order if r in counts.index]).dropna()

    plt.figure(figsize=(8, 5))
    plt.bar(counts.index, counts.values)
    plt.title("Cantidad de registros por nivel de riesgo")
    plt.xlabel("Nivel de riesgo")
    plt.ylabel("Cantidad")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)

    if show:
        plt.show()
    else:
        plt.close()

    return output_path


def plot_mission_states(df: pd.DataFrame, output_name: str, show: bool = False) -> Path:
    output_path = FIGURES_DIR / f"{output_name}_estados_mision.png"

    counts = df["mission_state"].value_counts()

    plt.figure(figsize=(10, 5))
    plt.barh(counts.index, counts.values)
    plt.title("Estados de misión registrados")
    plt.xlabel("Cantidad")
    plt.ylabel("Estado de misión")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)

    if show:
        plt.show()
    else:
        plt.close()

    return output_path


# ============================================================
# Reporte
# ============================================================

def generate_summary(df: pd.DataFrame, csv_path: Path) -> dict:
    initial = df.iloc[0]
    final = df.iloc[-1]

    summary = {
        "csv_path": str(csv_path),
        "records": int(len(df)),
        "start_time": str(initial.get("timestamp", "")),
        "end_time": str(final.get("timestamp", "")),
        "estimated_distance": round(estimate_distance(df), 2),
        "max_risk": get_max_risk(df),
        "final_risk": str(final.get("risk_level", "Desconocido")),
        "final_state": str(final.get("mission_state", "SIN_ESTADO")),
        "final_action": str(final.get("recommended_action", "")),
        "final_battery": round(float(final.get("battery", 0)), 2),
        "final_gas": round(float(final.get("gas_ppm", 0)), 2),
        "final_temperature": round(float(final.get("temperature", 0)), 2),
        "final_vibration": round(float(final.get("vibration", 0)), 2),
        "final_inclination": round(float(final.get("inclination", 0)), 2),
        "final_obstacle_distance": round(float(final.get("obstacle_distance", 0)), 2),
        "person_detected": int(df["person_detected"].max()),
        "alerts_count": count_alerts(df),
        "unique_alerts": get_unique_alerts(df),
    }

    return summary


def create_markdown_report(
    df: pd.DataFrame,
    summary: dict,
    figures: list[Path],
    output_name: str,
) -> Path:
    report_path = REPORT_DIR / f"{output_name}.md"

    lines = []

    lines.append("# RescueTwin AI - Reporte de misión")
    lines.append("")
    lines.append(f"Fecha de generación: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(
        "La misión simula el comportamiento de un robot cuadrúpedo de rescate en un entorno de derrumbe. "
        "Durante la ejecución, el sistema registra la posición del robot, sensores ambientales, nivel de riesgo "
        "estimado por IA, decisiones autónomas y alertas enviadas a la base."
    )
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Archivo CSV analizado | `{summary['csv_path']}` |")
    lines.append(f"| Registros analizados | {summary['records']} |")
    lines.append(f"| Distancia estimada recorrida | {summary['estimated_distance']} m |")
    lines.append(f"| Riesgo máximo detectado | {summary['max_risk']} |")
    lines.append(f"| Riesgo final | {summary['final_risk']} |")
    lines.append(f"| Estado final de misión | {summary['final_state']} |")
    lines.append(f"| Acción final recomendada | {summary['final_action']} |")
    lines.append(f"| Batería final | {summary['final_battery']} % |")
    lines.append(f"| Gas final | {summary['final_gas']} ppm |")
    lines.append(f"| Temperatura final | {summary['final_temperature']} °C |")
    lines.append(f"| Vibración final | {summary['final_vibration']} |")
    lines.append(f"| Inclinación final | {summary['final_inclination']} ° |")
    lines.append(f"| Distancia final a obstáculo | {summary['final_obstacle_distance']} m |")
    lines.append(f"| Persona detectada | {'Sí' if summary['person_detected'] == 1 else 'No'} |")
    lines.append(f"| Alertas registradas | {summary['alerts_count']} |")
    lines.append("")

    lines.append("## 2. Alertas enviadas a la base")
    lines.append("")
    if summary["unique_alerts"]:
        for alert in summary["unique_alerts"]:
            lines.append(f"- {alert}")
    else:
        lines.append("No se registraron alertas a la base durante esta misión.")
    lines.append("")

    lines.append("## 3. Gráficos generados")
    lines.append("")
    for fig in figures:
        relative = fig.relative_to(PROJECT_DIR)
        lines.append(f"![{fig.stem}](../../{relative.as_posix()})")
        lines.append("")

    lines.append("## 4. Últimos registros de la misión")
    lines.append("")
    cols_to_show = [
        "timestamp",
        "x",
        "y",
        "mission_state",
        "risk_level",
        "temperature",
        "gas_ppm",
        "vibration",
        "inclination",
        "battery",
        "obstacle_distance",
        "person_detected",
    ]

    cols_to_show = [col for col in cols_to_show if col in df.columns]
    tail = df[cols_to_show].tail(10)

    lines.append(tail.to_markdown(index=False))
    lines.append("")

    lines.append("## 5. Interpretación")
    lines.append("")
    lines.append(
        "El reporte permite analizar si el robot atravesó zonas peligrosas, si el modelo IA detectó un aumento "
        "en el nivel de riesgo y si el sistema autónomo reaccionó con decisiones de navegación o alertas. "
        "La ruta 2D permite visualizar el desplazamiento del robot en el escenario, mientras que las series "
        "temporales muestran cómo evolucionaron las variables críticas de la misión."
    )
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def create_summary_csv(summary: dict, output_name: str) -> Path:
    output_path = REPORT_DIR / f"{output_name}_resumen.csv"

    summary_flat = summary.copy()
    summary_flat["unique_alerts"] = " | ".join(summary.get("unique_alerts", []))

    pd.DataFrame([summary_flat]).to_csv(output_path, index=False)
    return output_path


# ============================================================
# Main
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un reporte de misión a partir de la bitácora CSV de RescueTwin AI."
    )

    parser.add_argument(
        "csv_path",
        nargs="?",
        default=None,
        help="Ruta opcional a un CSV de misión. Si no se indica, usa el más reciente.",
    )

    parser.add_argument(
        "--output-name",
        default=None,
        help="Nombre base de los archivos generados.",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="Muestra los gráficos en pantalla además de guardarlos.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ensure_dirs()

    if args.csv_path:
        csv_path = Path(args.csv_path)
    else:
        csv_path = find_latest_csv()

    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV indicado: {csv_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = args.output_name or f"mission_report_{timestamp}"

    print_step(f"Leyendo CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    df = normalize_columns(df)

    if df.empty:
        raise ValueError(f"El CSV no contiene registros: {csv_path}")

    print_step("Generando resumen")
    summary = generate_summary(df, csv_path)

    print_step("Generando gráficos")
    figures = []
    figures.append(plot_route(df, output_name, show=args.show))
    figures.extend(plot_sensor_series(df, output_name, show=args.show))
    figures.append(plot_risk_counts(df, output_name, show=args.show))
    figures.append(plot_mission_states(df, output_name, show=args.show))

    print_step("Generando reporte Markdown")
    report_path = create_markdown_report(df, summary, figures, output_name)

    print_step("Generando CSV de resumen")
    summary_csv = create_summary_csv(summary, output_name)

    print("")
    print("Reporte generado correctamente.")
    print(f"Markdown: {report_path}")
    print(f"Resumen CSV: {summary_csv}")
    print("Figuras:")
    for fig in figures:
        print(f"- {fig}")


if __name__ == "__main__":
    main()
