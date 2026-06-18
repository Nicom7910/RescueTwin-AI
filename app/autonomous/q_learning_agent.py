import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.autonomous.actions import ACTIONS
from app.autonomous.state import PerceivedState


class QLearningAgent:
    """
    Agente Q-Learning tabular.

    Aprende una política estado -> acción a partir de experiencia.
    No usa reglas del tipo "si pasa X, hacer Y".

    Mejora anti-bucles:
    - permite recibir acciones bloqueadas temporalmente
    - si una acción falló muchas veces en la misma situación, el runner puede excluirla
    - el agente elige la mejor acción disponible según la Q-table
    """

    def __init__(
        self,
        actions: Optional[List[str]] = None,
        learning_rate: float = 0.15,
        discount_factor: float = 0.90,
        epsilon: float = 0.25,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.05,
        seed: Optional[int] = None,
    ):
        self.actions = actions or ACTIONS
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.random = random.Random(seed)
        self.q_table: Dict[str, Dict[str, float]] = {}

    def discretize_state(self, state: PerceivedState) -> str:
        x_bucket = state.x // 2
        y_bucket = state.y // 2
        visited_bucket = "ALTA" if state.visited_ratio >= 0.45 else "MEDIA" if state.visited_ratio >= 0.20 else "BAJA"

        return "|".join(
            [
                f"x{x_bucket}",
                f"y{y_bucket}",
                f"d{state.direction}",
                f"risk{state.risk_level}",
                f"battery{state.battery_level}",
                f"obs{state.obstacle_level}",
                f"victim{int(state.victim_detected)}",
                f"visited{visited_bucket}",
            ]
        )

    def choose_action(
        self,
        state: PerceivedState,
        training: bool = True,
        blocked_actions: Optional[Set[str]] = None,
    ) -> str:
        """
        Elige una acción usando epsilon-greedy.

        blocked_actions no representa escenarios hardcodeados.
        Es una restricción dinámica de seguridad: acciones que fallaron
        repetidamente en la posición actual quedan temporalmente excluidas.
        """

        state_key = self.discretize_state(state)
        self._ensure_state(state_key)

        blocked_actions = blocked_actions or set()
        available_actions = [action for action in self.actions if action not in blocked_actions]

        if not available_actions:
            available_actions = list(self.actions)

        if training and self.random.random() < self.epsilon:
            return self.random.choice(available_actions)

        q_values = self.q_table[state_key]
        return max(available_actions, key=lambda action: q_values.get(action, 0.0))

    def learn(
        self,
        previous_state: PerceivedState,
        action: str,
        reward: float,
        next_state: PerceivedState,
    ) -> None:
        previous_key = self.discretize_state(previous_state)
        next_key = self.discretize_state(next_state)

        self._ensure_state(previous_key)
        self._ensure_state(next_key)

        current_q = self.q_table[previous_key][action]
        best_next_q = max(self.q_table[next_key].values())

        updated_q = current_q + self.learning_rate * (
            reward + self.discount_factor * best_next_q - current_q
        )

        self.q_table[previous_key][action] = round(updated_q, 5)

    def decay_exploration(self) -> None:
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def _ensure_state(self, state_key: str) -> None:
        if state_key not in self.q_table:
            self.q_table[state_key] = {action: 0.0 for action in self.actions}

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "epsilon": self.epsilon,
            "q_table": self.q_table,
        }

        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        path = Path(path)

        if not path.exists():
            return

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.learning_rate = payload.get("learning_rate", self.learning_rate)
        self.discount_factor = payload.get("discount_factor", self.discount_factor)
        self.epsilon = payload.get("epsilon", self.epsilon)
        self.q_table = payload.get("q_table", {})
