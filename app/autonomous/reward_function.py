from typing import Set, Tuple

from app.autonomous.actions import RobotAction
from app.autonomous.procedural_world import StepResult
from app.autonomous.state import PerceivedState


Position = Tuple[int, int]


class RewardFunction:
    """
    Función de recompensa del agente.

    No define decisiones fijas. Define objetivos generales:
    - explorar
    - evitar daño
    - encontrar víctimas
    - administrar batería
    - volver a base cuando corresponde
    - evitar bucles y acciones inútiles
    """

    def calculate(
        self,
        previous_state: PerceivedState,
        action: str,
        result: StepResult,
        previous_position: Position,
        current_position: Position,
        previously_visited: Set[Position],
        repeated_action_count: int = 1,
        same_position_count: int = 1,
        recent_position_revisits: int = 0,
    ) -> float:
        reward = -0.2

        if result.collided:
            reward -= 25

        if result.moved:
            reward += 2

        if current_position not in previously_visited:
            reward += 8

        if result.reached_victim:
            reward += 60

        if result.returned_base and previous_state.battery_level == "BAJA":
            reward += 60

        if previous_state.risk_level == "ALTO" and action == RobotAction.AVANZAR.value:
            reward -= 12

        if previous_state.risk_level == "ALTO" and action in {
            RobotAction.GIRAR_IZQUIERDA.value,
            RobotAction.GIRAR_DERECHA.value,
            RobotAction.RETROCEDER.value,
            RobotAction.ENVIAR_ALERTA.value,
        }:
            reward += 6

        if previous_state.victim_detected and action in {
            RobotAction.ESCANEAR.value,
            RobotAction.ENVIAR_ALERTA.value,
            RobotAction.AVANZAR.value,
        }:
            reward += 10

        if previous_state.battery_level == "BAJA" and action == RobotAction.VOLVER_BASE.value:
            reward += 20

        if previous_state.battery_level == "BAJA" and action not in {
            RobotAction.VOLVER_BASE.value,
            RobotAction.ENVIAR_ALERTA.value,
        }:
            reward -= 8

        # Penalización genérica por repetición de acciones.
        # No depende de un escenario específico: solo castiga quedarse haciendo lo mismo.
        if repeated_action_count >= 3:
            reward -= 3 * (repeated_action_count - 2)

        # Penalización por estancamiento en la misma posición.
        if same_position_count >= 3:
            reward -= 4 * (same_position_count - 2)

        # Penalización más fuerte si intenta moverse y no logra cambiar de posición.
        if action in {RobotAction.AVANZAR.value, RobotAction.RETROCEDER.value} and not result.moved:
            reward -= 8

        # Penalización por escanear repetidamente sin encontrar una víctima real.
        if action == RobotAction.ESCANEAR.value and not previous_state.victim_detected and repeated_action_count >= 2:
            reward -= 4

        # Penalización por alertar repetidamente sin nueva información.
        if action == RobotAction.ENVIAR_ALERTA.value and not previous_state.victim_detected and repeated_action_count >= 2:
            reward -= 4

        # Pequeño incentivo para girar o retroceder cuando el obstáculo está cerca.
        if previous_state.obstacle_level == "CERCA" and action in {
            RobotAction.GIRAR_IZQUIERDA.value,
            RobotAction.GIRAR_DERECHA.value,
            RobotAction.RETROCEDER.value,
        }:
            reward += 5

        # Si la batería está baja, insistir en acciones que no sean volver a base
        # debe ser bastante costoso.
        if previous_state.battery_level == "BAJA" and action != RobotAction.VOLVER_BASE.value:
            reward -= 10

        # Volver a base con batería baja debe ser claramente preferible.
        if previous_state.battery_level == "BAJA" and action == RobotAction.VOLVER_BASE.value:
            if result.returned_base:
                reward += 25
            else:
                reward += 10

        # Penalización por rebotar entre celdas recientes.
        # Evita patrones como AVANZAR ↔ RETROCEDER.
        if recent_position_revisits >= 2:
            reward -= 6 * recent_position_revisits

        # Si el robot vuelve a una posición ya visitada y no hay víctima,
        # se desalienta la repetición.
        if current_position in previously_visited and not previous_state.victim_detected:
            reward -= 3

        # Si está con batería baja y VOLVER_BASE no cambia la posición,
        # entonces la acción no está ayudando realmente.
        if (
            previous_state.battery_level == "BAJA"
            and action == RobotAction.VOLVER_BASE.value
            and current_position == previous_position
        ):
            reward -= 25
        
        return round(reward, 3)
