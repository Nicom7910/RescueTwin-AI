import csv
from pathlib import Path
from typing import Dict, List


class ExperienceMemory:
    """
    Guarda la experiencia del robot.

    Este archivo permite ver cómo aprende:
    estado, acción, recompensa, nuevo estado y resultado.
    """

    FIELDNAMES = [
        "episode",
        "step",
        "x",
        "y",
        "direction",
        "risk_level",
        "risk_score",
        "battery_level",
        "obstacle_level",
        "victim_detected",
        "blocked_actions",
        "repeated_action_count",
        "same_position_count",
        "action",
        "reward",
        "next_x",
        "next_y",
        "next_risk_level",
        "collided",
        "reached_victim",
        "remaining_victims",
        "battery",
        "message",
    ]

    def __init__(self):
        self.rows: List[Dict] = []

    def add(self, row: Dict) -> None:
        self.rows.append(row)

    def save_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()

            for row in self.rows:
                writer.writerow({field: row.get(field, "") for field in self.FIELDNAMES})
