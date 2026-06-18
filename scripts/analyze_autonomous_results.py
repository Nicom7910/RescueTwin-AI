import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPORTS_DIR = Path("reports/autonomous_missions")
SUMMARY_PATH = REPORTS_DIR / "autonomous_summary.json"
EXPERIENCE_LOG_PATH = REPORTS_DIR / "experience_log.csv"
OUTPUT_DIR = REPORTS_DIR / "analysis"


def load_summary() -> dict:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró {SUMMARY_PATH}. "
            "Primero ejecutá una misión autónoma."
        )

    with SUMMARY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_experience_log() -> pd.DataFrame:
    if not EXPERIENCE_LOG_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró {EXPERIENCE_LOG_PATH}. "
            "Primero ejecutá una misión autónoma."
        )

    df = pd.read_csv(EXPERIENCE_LOG_PATH)

    default_columns = {
        "escape_mode": False,
        "return_to_base_mode": False,
        "action": "DESCONOCIDA",
        "risk_level": "DESCONOCIDO",
        "reward": 0.0,
        "battery_level": "DESCONOCIDO",
        "obstacle_level": "DESCONOCIDO",
        "victim_detected": False,
    }

    for column, default_value in default_columns.items():
        if column not in df.columns:
            df[column] = default_value

    return df


def as_boolean_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes", "si", "sí"])


def format_metric_value(value):
    """
    Evita salidas como 4085.0000.

    - Si es entero, muestra 4085.
    - Si es decimal, muestra hasta 3 decimales útiles.
    - Si es texto, lo deja igual.
    """

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))

        return f"{value:.3f}".rstrip("0").rstrip(".")

    return str(value)


def plot_total_reward_by_episode(summary: dict) -> None:
    summaries = summary["summaries"]

    episodes = [item["episode"] for item in summaries]
    rewards = [item["total_reward"] for item in summaries]

    plt.figure(figsize=(10, 5))
    plt.plot(episodes, rewards, marker="o")
    plt.title("Recompensa total por episodio")
    plt.xlabel("Episodio")
    plt.ylabel("Recompensa total")
    plt.grid(True)
    plt.tight_layout()

    output_path = OUTPUT_DIR / "total_reward_by_episode.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_steps_by_episode(summary: dict) -> None:
    summaries = summary["summaries"]

    episodes = [item["episode"] for item in summaries]
    steps = [item["steps"] for item in summaries]

    plt.figure(figsize=(10, 5))
    plt.plot(episodes, steps, marker="o")
    plt.title("Cantidad de pasos por episodio")
    plt.xlabel("Episodio")
    plt.ylabel("Pasos")
    plt.grid(True)
    plt.tight_layout()

    output_path = OUTPUT_DIR / "steps_by_episode.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_finish_reasons(summary: dict) -> None:
    summaries = summary["summaries"]

    finish_reasons = pd.Series(
        [item.get("finish_reason", "unknown") for item in summaries]
    )

    counts = finish_reasons.value_counts()

    plt.figure(figsize=(8, 5))
    counts.plot(kind="bar")
    plt.title("Motivo de finalización de las misiones")
    plt.xlabel("Motivo")
    plt.ylabel("Cantidad de episodios")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    output_path = OUTPUT_DIR / "finish_reasons.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_actions_distribution(experience_log: pd.DataFrame) -> None:
    action_counts = experience_log["action"].value_counts()

    plt.figure(figsize=(10, 5))
    action_counts.plot(kind="bar")
    plt.title("Distribución de acciones ejecutadas")
    plt.xlabel("Acción")
    plt.ylabel("Cantidad")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    output_path = OUTPUT_DIR / "actions_distribution.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_modes_usage(experience_log: pd.DataFrame) -> None:
    escape_count = as_boolean_series(experience_log["escape_mode"]).sum()
    return_count = as_boolean_series(experience_log["return_to_base_mode"]).sum()

    values = pd.Series(
        {
            "Modo escape": int(escape_count),
            "Modo retorno": int(return_count),
        }
    )

    plt.figure(figsize=(7, 5))
    values.plot(kind="bar")
    plt.title("Uso de modos operativos")
    plt.xlabel("Modo")
    plt.ylabel("Cantidad de pasos")
    plt.xticks(rotation=0)
    plt.tight_layout()

    output_path = OUTPUT_DIR / "modes_usage.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_risk_distribution(experience_log: pd.DataFrame) -> None:
    risk_counts = experience_log["risk_level"].value_counts()

    plt.figure(figsize=(7, 5))
    risk_counts.plot(kind="bar")
    plt.title("Distribución de niveles de riesgo percibidos")
    plt.xlabel("Nivel de riesgo")
    plt.ylabel("Cantidad de lecturas")
    plt.xticks(rotation=0)
    plt.tight_layout()

    output_path = OUTPUT_DIR / "risk_distribution.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_battery_distribution(experience_log: pd.DataFrame) -> None:
    battery_counts = experience_log["battery_level"].value_counts()

    plt.figure(figsize=(7, 5))
    battery_counts.plot(kind="bar")
    plt.title("Distribución de niveles de batería")
    plt.xlabel("Nivel de batería")
    plt.ylabel("Cantidad de lecturas")
    plt.xticks(rotation=0)
    plt.tight_layout()

    output_path = OUTPUT_DIR / "battery_distribution.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_obstacle_distribution(experience_log: pd.DataFrame) -> None:
    obstacle_counts = experience_log["obstacle_level"].value_counts()

    plt.figure(figsize=(7, 5))
    obstacle_counts.plot(kind="bar")
    plt.title("Distribución de cercanía a obstáculos")
    plt.xlabel("Nivel de obstáculo")
    plt.ylabel("Cantidad de lecturas")
    plt.xticks(rotation=0)
    plt.tight_layout()

    output_path = OUTPUT_DIR / "obstacle_distribution.png"
    plt.savefig(output_path, dpi=150)
    plt.close()


def build_metrics_table(summary: dict, experience_log: pd.DataFrame) -> pd.DataFrame:
    summaries = summary["summaries"]

    total_episodes = len(summaries)
    q_table_states = summary.get("q_table_states", 0)
    epsilon_final = summary.get("epsilon_final", 0)

    returned_base = sum(
        1
        for item in summaries
        if item.get("finish_reason") == "returned_base_low_battery"
    )

    all_victims_found = sum(
        1
        for item in summaries
        if item.get("finish_reason") == "all_victims_found"
    )

    battery_depleted = sum(
        1
        for item in summaries
        if item.get("finish_reason") == "battery_depleted"
    )

    max_steps = sum(
        1
        for item in summaries
        if item.get("finish_reason") == "max_steps"
    )

    total_victims_found = sum(item.get("victims_found", 0) for item in summaries)

    if total_episodes > 0:
        average_reward = sum(item["total_reward"] for item in summaries) / total_episodes
        average_steps = sum(item["steps"] for item in summaries) / total_episodes
        average_visited_ratio = (
            sum(item["visited_ratio"] for item in summaries) / total_episodes
        )
    else:
        average_reward = 0
        average_steps = 0
        average_visited_ratio = 0

    escape_steps = as_boolean_series(experience_log["escape_mode"]).sum()
    return_steps = as_boolean_series(experience_log["return_to_base_mode"]).sum()
    victim_detected_steps = as_boolean_series(experience_log["victim_detected"]).sum()

    positive_rewards = (experience_log["reward"] > 0).sum()
    negative_rewards = (experience_log["reward"] < 0).sum()

    metrics = [
        ("Episodios ejecutados", total_episodes),
        ("Estados aprendidos en Q-table", q_table_states),
        ("Epsilon final", epsilon_final),
        ("Misiones finalizadas por retorno a base", returned_base),
        ("Misiones finalizadas por víctimas encontradas", all_victims_found),
        ("Misiones finalizadas por batería agotada", battery_depleted),
        ("Misiones finalizadas por max_steps", max_steps),
        ("Víctimas encontradas", total_victims_found),
        ("Recompensa promedio", average_reward),
        ("Pasos promedio por episodio", average_steps),
        ("Ratio promedio de exploración", average_visited_ratio),
        ("Pasos en modo escape", int(escape_steps)),
        ("Pasos en modo retorno", int(return_steps)),
        ("Pasos con víctima detectada", int(victim_detected_steps)),
        ("Acciones con recompensa positiva", int(positive_rewards)),
        ("Acciones con recompensa negativa", int(negative_rewards)),
    ]

    formatted_metrics = [
        (metric_name, format_metric_value(metric_value))
        for metric_name, metric_value in metrics
    ]

    return pd.DataFrame(formatted_metrics, columns=["Métrica", "Valor"])


def save_markdown_report(metrics_df: pd.DataFrame) -> None:
    output_path = OUTPUT_DIR / "autonomous_metrics_report.md"

    lines = [
        "# Reporte de métricas del agente autónomo",
        "",
        "Este reporte resume el comportamiento del agente Q-Learning en las misiones autónomas.",
        "",
        "## Métricas generales",
        "",
        metrics_df.to_markdown(index=False),
        "",
        "## Gráficos generados",
        "",
        "- `total_reward_by_episode.png`",
        "- `steps_by_episode.png`",
        "- `finish_reasons.png`",
        "- `actions_distribution.png`",
        "- `modes_usage.png`",
        "- `risk_distribution.png`",
        "- `battery_distribution.png`",
        "- `obstacle_distribution.png`",
        "",
        "## Interpretación",
        "",
        "El agente autónomo utiliza Q-Learning para decidir acciones durante la misión. "
        "Además, incorpora reglas operativas de seguridad como modo retorno por batería baja, "
        "planificación BFS para regresar a base y modo escape ante estancamiento. "
        "Estas capas permiten que el robot mantenga comportamiento autónomo, pero con mayor "
        "seguridad y robustez ante obstáculos, bucles o baja batería.",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = load_summary()
    experience_log = load_experience_log()

    plot_total_reward_by_episode(summary)
    plot_steps_by_episode(summary)
    plot_finish_reasons(summary)
    plot_actions_distribution(experience_log)
    plot_modes_usage(experience_log)
    plot_risk_distribution(experience_log)
    plot_battery_distribution(experience_log)
    plot_obstacle_distribution(experience_log)

    metrics_df = build_metrics_table(summary, experience_log)

    metrics_csv_path = OUTPUT_DIR / "autonomous_metrics.csv"
    metrics_df.to_csv(metrics_csv_path, index=False)

    save_markdown_report(metrics_df)

    print("\n" + "=" * 90)
    print("ANÁLISIS DE MISIONES AUTÓNOMAS GENERADO")
    print("=" * 90)
    print()
    print(metrics_df.to_string(index=False))
    print()
    print("Archivos generados:")
    print(f"- {OUTPUT_DIR / 'autonomous_metrics.csv'}")
    print(f"- {OUTPUT_DIR / 'autonomous_metrics_report.md'}")
    print(f"- {OUTPUT_DIR / 'total_reward_by_episode.png'}")
    print(f"- {OUTPUT_DIR / 'steps_by_episode.png'}")
    print(f"- {OUTPUT_DIR / 'finish_reasons.png'}")
    print(f"- {OUTPUT_DIR / 'actions_distribution.png'}")
    print(f"- {OUTPUT_DIR / 'modes_usage.png'}")
    print(f"- {OUTPUT_DIR / 'risk_distribution.png'}")
    print(f"- {OUTPUT_DIR / 'battery_distribution.png'}")
    print(f"- {OUTPUT_DIR / 'obstacle_distribution.png'}")


if __name__ == "__main__":
    main()