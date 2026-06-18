import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.autonomous.mission_runner import AutonomousMissionRunner


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ejecuta misiones autónomas RescueTwin con Q-Learning nivel 1."
    )
    parser.add_argument("--episodes", type=int, default=10, help="Cantidad de misiones de entrenamiento.")
    parser.add_argument("--max-steps", type=int, default=80, help="Máximo de pasos por misión.")
    parser.add_argument("--seed", type=int, default=None, help="Semilla opcional para reproducibilidad.")
    parser.add_argument("--eval", action="store_true", help="Ejecuta sin exploración ni aprendizaje.")
    parser.add_argument("--quiet", action="store_true", help="Reduce la salida por consola.")
    return parser.parse_args()


def main():
    args = parse_args()

    runner = AutonomousMissionRunner(seed=args.seed)
    report = runner.run(
        episodes=args.episodes,
        max_steps=args.max_steps,
        training=not args.eval,
        verbose=not args.quiet,
    )

    print("\n" + "=" * 96)
    print("RESUMEN FINAL")
    print("=" * 96)
    print(f"Episodios ejecutados: {report['episodes']}")
    print(f"Estados aprendidos en Q-table: {report['q_table_states']}")
    print(f"Epsilon final: {report['epsilon_final']}")
    print("Archivos generados:")
    print("- models/autonomous/q_table.json")
    print("- reports/autonomous_missions/experience_log.csv")
    print("- reports/autonomous_missions/autonomous_summary.json")
    print("- reports/autonomous_missions/mission_XXX_known_map.txt")
    print("- reports/autonomous_missions/mission_XXX_trajectory.json")


if __name__ == "__main__":
    main()
