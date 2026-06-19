import json
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.autonomous.actions import RobotAction
from app.autonomous.experience_memory import ExperienceMemory
from app.autonomous.procedural_world import ProceduralWorld
from app.autonomous.q_learning_agent import QLearningAgent
from app.autonomous.reward_function import RewardFunction
from app.autonomous.sensor_fusion import SensorFusion


Position = Tuple[int, int]


class AutonomousMissionRunner:
    """
    Ejecuta misiones autónomas con aprendizaje Q-Learning.

    Mejoras incluidas:
    - control anti-bucles
    - modo búsqueda de víctima
    - navegación dirigida hacia víctima detectada
    - planificación BFS hacia víctima
    - modo retorno de emergencia por batería baja
    - modo escape ante estancamiento
    - exportación de trayectoria y mundo procedural para Unity
    """

    def __init__(
        self,
        output_dir: str | Path = "reports/autonomous_missions",
        q_table_path: str | Path = "models/autonomous/q_table.json",
        seed: Optional[int] = None,
    ):
        self.output_dir = Path(output_dir)
        self.q_table_path = Path(q_table_path)
        self.seed = seed

        self.agent = QLearningAgent(seed=seed)
        self.agent.load(self.q_table_path)

        self.sensor_fusion = SensorFusion()
        self.reward_function = RewardFunction()
        self.memory = ExperienceMemory()

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        episodes: int = 10,
        max_steps: int = 80,
        training: bool = True,
        verbose: bool = True,
    ) -> Dict:
        summaries: List[Dict] = []

        for episode in range(1, episodes + 1):
            world_seed = None if self.seed is None else self.seed + episode
            world = ProceduralWorld(seed=world_seed)

            summary = self._run_episode(
                episode=episode,
                world=world,
                max_steps=max_steps,
                training=training,
                verbose=verbose,
            )
            summaries.append(summary)

            if training:
                self.agent.decay_exploration()

        self.agent.save(self.q_table_path)
        self.memory.save_csv(self.output_dir / "experience_log.csv")

        final_report = {
            "episodes": episodes,
            "max_steps": max_steps,
            "training": training,
            "epsilon_final": round(self.agent.epsilon, 4),
            "q_table_states": len(self.agent.q_table),
            "summaries": summaries,
        }

        (self.output_dir / "autonomous_summary.json").write_text(
            json.dumps(final_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return final_report

    def _run_episode(
        self,
        episode: int,
        world: ProceduralWorld,
        max_steps: int,
        training: bool,
        verbose: bool,
    ) -> Dict:
        total_reward = 0.0
        victims_found = 0
        collisions = 0
        trajectory = []
        recent_steps: List[Dict] = []

        return_to_base_mode = False
        victim_search_mode = False
        victim_search_steps_remaining = 0
        victim_target: Optional[Position] = None

        finish_reason = "max_steps"
        last_victim_location: Optional[Position] = None

        if verbose:
            print("\n" + "=" * 96)
            print(
                f"MISIÓN AUTÓNOMA {episode} | mundo procedural | "
                f"víctimas iniciales={world.remaining_victims()}"
            )
            print("=" * 96)

        for step in range(1, max_steps + 1):
            reading = world.read_sensors()
            state = self.sensor_fusion.build_state(
                world.pose,
                reading,
                world.visited_ratio(),
            )

            previous_position = world.current_position()
            previously_visited = set(world.visited)

            # ---------------------------------------------------------------
            # Activación de búsqueda dirigida hacia víctima
            # ---------------------------------------------------------------
            if state.victim_detected and world.remaining_victims() > 0:
                nearest_victim = self._find_nearest_victim(world)

                if nearest_victim is not None:
                    victim_search_mode = True
                    victim_search_steps_remaining = 20
                    victim_target = nearest_victim

                    # Si estaba volviendo a base pero detecta víctima,
                    # prioriza la víctima. Esto hace que el caso 2 no ignore señales.
                    if state.battery_level != "BAJA":
                        return_to_base_mode = False

            if victim_search_steps_remaining <= 0 or world.remaining_victims() == 0:
                victim_search_mode = False
                victim_target = None

            # ---------------------------------------------------------------
            # Retorno a base
            # ---------------------------------------------------------------
            # Con batería baja se vuelve a base salvo que haya una víctima detectada
            # y todavía exista un objetivo de víctima activo.
            if (
                state.battery_level == "BAJA"
                and world.current_position() != world.base
                and not victim_search_mode
            ):
                return_to_base_mode = True

            blocked_actions = self._get_blocked_actions(
                recent_steps,
                previous_position,
            )
            blocked_actions.update(
                self._get_oscillation_blocked_actions(recent_steps)
            )
            blocked_actions.update(
                self._get_invalid_actions(
                    state=state,
                    world=world,
                    recent_steps=recent_steps,
                    victim_search_mode=victim_search_mode,
                )
            )

            if state.battery_level == "BAJA":
                blocked_actions.discard(RobotAction.VOLVER_BASE.value)

            if victim_search_mode:
                blocked_actions.add(RobotAction.VOLVER_BASE.value)
                blocked_actions.add(RobotAction.ENVIAR_ALERTA.value)

            escape_mode = self._is_stuck(recent_steps)

            if escape_mode and not victim_search_mode and state.battery_level != "BAJA":
                blocked_actions.add(RobotAction.ESCANEAR.value)
                blocked_actions.add(RobotAction.ENVIAR_ALERTA.value)

                if state.obstacle_level == "CERCA":
                    blocked_actions.add(RobotAction.AVANZAR.value)

            # ---------------------------------------------------------------
            # Selección de acción
            # ---------------------------------------------------------------
            if victim_search_mode and victim_target is not None:
                action = self._choose_action_towards_victim(
                    world=world,
                    target=victim_target,
                    blocked_actions=blocked_actions,
                )
                victim_search_steps_remaining -= 1

            elif return_to_base_mode and world.current_position() != world.base:
                action = RobotAction.VOLVER_BASE.value

            elif escape_mode and state.battery_level != "BAJA":
                action = self._choose_escape_action(
                    state=state,
                    recent_steps=recent_steps,
                    blocked_actions=blocked_actions,
                )

            else:
                action = self.agent.choose_action(
                    state,
                    training=training,
                    blocked_actions=blocked_actions,
                )

            result = world.apply_action(action)

            next_reading = world.read_sensors()
            next_state = self.sensor_fusion.build_state(
                world.pose,
                next_reading,
                world.visited_ratio(),
            )

            current_position = world.current_position()
            repeated_action_count = self._count_repeated_action(
                recent_steps,
                action,
            )
            same_position_count = self._count_same_position(
                recent_steps,
                current_position,
            )

            recent_positions = [item["position"] for item in recent_steps[-8:]]
            recent_position_revisits = recent_positions.count(current_position)

            reward = self.reward_function.calculate(
                previous_state=state,
                action=action,
                result=result,
                previous_position=previous_position,
                current_position=current_position,
                previously_visited=previously_visited,
                repeated_action_count=repeated_action_count,
                same_position_count=same_position_count,
                recent_position_revisits=recent_position_revisits,
            )

            # Recompensas extra por búsqueda dirigida.
            if victim_search_mode and victim_target is not None:
                distance_before = self._manhattan(previous_position, victim_target)
                distance_after = self._manhattan(current_position, victim_target)

                if result.reached_victim:
                    reward += 120
                elif distance_after < distance_before:
                    reward += 25
                elif distance_after > distance_before:
                    reward -= 30

                if action == RobotAction.VOLVER_BASE.value:
                    reward -= 80

            if training:
                self.agent.learn(state, action, reward, next_state)

            total_reward += reward
            victims_found += int(result.reached_victim)
            collisions += int(result.collided)

            victim_found_x = next_state.x if result.reached_victim else None
            victim_found_y = next_state.y if result.reached_victim else None

            if result.reached_victim:
                last_victim_location = current_position
                victim_search_mode = False
                victim_search_steps_remaining = 0
                victim_target = None

            row = {
                "episode": episode,
                "step": step,
                "x": state.x,
                "y": state.y,
                "direction": state.direction,
                "risk_level": state.risk_level,
                "risk_score": state.risk_score,
                "battery_level": state.battery_level,
                "obstacle_level": state.obstacle_level,
                "victim_detected": state.victim_detected,
                "victim_search_mode": victim_search_mode,
                "victim_search_steps_remaining": victim_search_steps_remaining,
                "victim_target_x": victim_target[0] if victim_target else None,
                "victim_target_y": victim_target[1] if victim_target else None,
                "victim_found": result.reached_victim,
                "victim_x": victim_found_x,
                "victim_y": victim_found_y,
                "blocked_actions": ",".join(sorted(blocked_actions)),
                "repeated_action_count": repeated_action_count,
                "same_position_count": same_position_count,
                "recent_position_revisits": recent_position_revisits,
                "escape_mode": escape_mode,
                "return_to_base_mode": return_to_base_mode,
                "action": action,
                "reward": reward,
                "next_x": next_state.x,
                "next_y": next_state.y,
                "next_risk_level": next_state.risk_level,
                "collided": result.collided,
                "reached_victim": result.reached_victim,
                "remaining_victims": world.remaining_victims(),
                "battery": round(world.battery, 2),
                "message": result.message,
            }

            self.memory.add(row)

            recent_steps.append(
                {
                    "position": current_position,
                    "previous_position": previous_position,
                    "action": action,
                    "moved": result.moved,
                    "collided": result.collided,
                    "victim_detected": state.victim_detected,
                    "victim_search_mode": victim_search_mode,
                    "victim_target": victim_target,
                    "reward": reward,
                }
            )
            recent_steps = recent_steps[-10:]

            trajectory.append(
                {
                    "step": step,
                    "x": next_state.x,
                    "y": next_state.y,
                    "action": action,
                    "risk_level": next_state.risk_level,
                    "battery_level": next_state.battery_level,
                    "blocked_actions": sorted(blocked_actions),
                    "escape_mode": escape_mode,
                    "return_to_base_mode": return_to_base_mode,
                    "victim_detected": next_state.victim_detected,
                    "victim_search_mode": victim_search_mode,
                    "victim_target_x": victim_target[0] if victim_target else None,
                    "victim_target_y": victim_target[1] if victim_target else None,
                    "victim_found": result.reached_victim,
                    "victim_x": victim_found_x,
                    "victim_y": victim_found_y,
                    "message": result.message,
                }
            )

            if verbose:
                blocked_text = (
                    f" | bloqueadas={','.join(sorted(blocked_actions))}"
                    if blocked_actions
                    else ""
                )

                if return_to_base_mode:
                    mode_text = " | modo=RETORNO"
                elif victim_search_mode:
                    mode_text = " | modo=BÚSQUEDA_VÍCTIMA"
                elif escape_mode:
                    mode_text = " | modo=ESCAPE"
                else:
                    mode_text = ""

                victim_text = ""

                if result.reached_victim:
                    victim_text = f" | víctima_localizada=({next_state.x},{next_state.y})"
                elif victim_search_mode and victim_target is not None:
                    victim_text = f" | objetivo_víctima=({victim_target[0]},{victim_target[1]})"
                elif state.victim_detected:
                    victim_text = " | señal_víctima=True"

                print(
                    f"t={step:03d} | pos=({state.x:02d},{state.y:02d}) "
                    f"dir={state.direction} "
                    f"| riesgo={state.risk_level:<5}({state.risk_score:.2f}) "
                    f"| bat={state.battery_level:<5} "
                    f"| obs={state.obstacle_level:<5} "
                    f"| víctima={str(state.victim_detected):<5} "
                    f"| acción={action:<15} "
                    f"| reward={reward:>6.2f}"
                    f"{blocked_text}"
                    f"{mode_text}"
                    f"{victim_text} "
                    f"| {result.message}"
                )

            if result.returned_base and state.battery_level == "BAJA":
                finish_reason = "returned_base_low_battery"
                if verbose:
                    print("Misión finalizada: el robot volvió a base con batería baja.")
                break

            if world.battery <= 0:
                finish_reason = "battery_depleted"
                if verbose:
                    print("Misión finalizada: batería agotada.")
                break

            if world.remaining_victims() == 0:
                finish_reason = "all_victims_found"
                if verbose:
                    print("Misión finalizada: todas las posibles víctimas fueron localizadas.")
                break

        map_path = self.output_dir / f"mission_{episode:03d}_known_map.txt"
        map_path.write_text(
            world.render_ascii(reveal_world=False),
            encoding="utf-8",
        )

        trajectory_path = self.output_dir / f"mission_{episode:03d}_trajectory.json"
        trajectory_path.write_text(
            json.dumps(trajectory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        world_path = self.output_dir / f"mission_{episode:03d}_world.json"
        world_path.write_text(
            json.dumps(
                world.to_unity_world_dict(mission_number=episode),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        last_victim_location_dict = None

        if last_victim_location is not None:
            last_victim_location_dict = {
                "x": last_victim_location[0],
                "y": last_victim_location[1],
            }

        return {
            "episode": episode,
            "steps": step,
            "total_reward": round(total_reward, 3),
            "victims_found": victims_found,
            "remaining_victims": world.remaining_victims(),
            "collisions": collisions,
            "visited_ratio": round(world.visited_ratio(), 3),
            "battery_final": round(world.battery, 2),
            "finish_reason": finish_reason,
            "last_victim_location": last_victim_location_dict,
            "known_map_file": str(map_path),
            "trajectory_file": str(trajectory_path),
            "world_file": str(world_path),
        }

    # -------------------------------------------------------------------------
    # Navegación hacia víctima
    # -------------------------------------------------------------------------

    def _find_nearest_victim(self, world: ProceduralWorld) -> Optional[Position]:
        if not world.victims:
            return None

        current = world.current_position()

        return min(
            world.victims,
            key=lambda victim: self._manhattan(current, victim),
        )

    def _choose_action_towards_victim(
        self,
        world: ProceduralWorld,
        target: Position,
        blocked_actions: Set[str],
    ) -> str:
        """
        Decide una acción concreta para avanzar hacia la víctima.

        Usa BFS sobre el mapa procedural para evitar obstáculos.
        Cuando hay señal de víctima, esta política tiene prioridad sobre Q-Learning.
        """

        current = world.current_position()

        if current == target:
            return RobotAction.ESCANEAR.value

        path = self._find_path(
            world=world,
            start=current,
            target=target,
        )

        if len(path) < 2:
            return self._choose_victim_search_fallback(
                world=world,
                blocked_actions=blocked_actions,
            )

        next_position = path[1]
        desired_direction = self._direction_from_to(current, next_position)

        if desired_direction is None:
            return self._choose_victim_search_fallback(
                world=world,
                blocked_actions=blocked_actions,
            )

        if world.pose.direction == desired_direction:
            return RobotAction.AVANZAR.value

        return self._turn_action_towards_direction(
            current_direction=world.pose.direction,
            desired_direction=desired_direction,
        )

    def _find_path(
        self,
        world: ProceduralWorld,
        start: Position,
        target: Position,
    ) -> List[Position]:
        queue = deque([start])
        came_from: Dict[Position, Optional[Position]] = {start: None}

        while queue:
            current = queue.popleft()

            if current == target:
                break

            for neighbor in self._neighbors(world, current):
                if neighbor in came_from:
                    continue

                came_from[neighbor] = current
                queue.append(neighbor)

        if target not in came_from:
            return []

        path = []
        current: Optional[Position] = target

        while current is not None:
            path.append(current)
            current = came_from[current]

        path.reverse()

        return path

    def _neighbors(self, world: ProceduralWorld, position: Position) -> List[Position]:
        x, y = position

        candidates = [
            (x, y - 1),
            (x + 1, y),
            (x, y + 1),
            (x - 1, y),
        ]

        return [
            candidate
            for candidate in candidates
            if world.in_bounds(candidate) and candidate not in world.obstacles
        ]

    def _direction_from_to(
        self,
        current: Position,
        next_position: Position,
    ) -> Optional[str]:
        cx, cy = current
        nx, ny = next_position

        if nx == cx and ny == cy - 1:
            return "N"

        if nx == cx + 1 and ny == cy:
            return "E"

        if nx == cx and ny == cy + 1:
            return "S"

        if nx == cx - 1 and ny == cy:
            return "W"

        return None

    def _turn_action_towards_direction(
        self,
        current_direction: str,
        desired_direction: str,
    ) -> str:
        directions = ["N", "E", "S", "W"]

        current_index = directions.index(current_direction)
        desired_index = directions.index(desired_direction)

        clockwise_distance = (desired_index - current_index) % 4
        counter_clockwise_distance = (current_index - desired_index) % 4

        if clockwise_distance <= counter_clockwise_distance:
            return RobotAction.GIRAR_DERECHA.value

        return RobotAction.GIRAR_IZQUIERDA.value

    def _choose_victim_search_fallback(
        self,
        world: ProceduralWorld,
        blocked_actions: Set[str],
    ) -> str:
        preferred_actions = [
            RobotAction.ESCANEAR.value,
            RobotAction.GIRAR_DERECHA.value,
            RobotAction.GIRAR_IZQUIERDA.value,
            RobotAction.AVANZAR.value,
            RobotAction.RETROCEDER.value,
        ]

        for action in preferred_actions:
            if action not in blocked_actions:
                return action

        return RobotAction.GIRAR_DERECHA.value

    def _manhattan(self, first: Position, second: Position) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])

    # -------------------------------------------------------------------------
    # Bloqueos y anti-bucles
    # -------------------------------------------------------------------------

    def _get_blocked_actions(
        self,
        recent_steps: List[Dict],
        current_position: Position,
    ) -> Set[str]:
        if not recent_steps:
            return set()

        blocked: Set[str] = set()

        same_position_steps = [
            item
            for item in recent_steps[-6:]
            if item["position"] == current_position
            or item["previous_position"] == current_position
        ]

        if len(same_position_steps) < 2:
            return blocked

        last_actions = [item["action"] for item in same_position_steps[-4:]]

        last_failed_moves = [
            item
            for item in same_position_steps[-4:]
            if item["action"]
            in {
                RobotAction.AVANZAR.value,
                RobotAction.RETROCEDER.value,
            }
            and not item["moved"]
        ]

        for move_action in {
            RobotAction.AVANZAR.value,
            RobotAction.RETROCEDER.value,
        }:
            failures = [
                item
                for item in last_failed_moves
                if item["action"] == move_action
            ]

            if len(failures) >= 2:
                blocked.add(move_action)

        for action in {
            RobotAction.ESCANEAR.value,
            RobotAction.ENVIAR_ALERTA.value,
            RobotAction.GIRAR_IZQUIERDA.value,
            RobotAction.GIRAR_DERECHA.value,
        }:
            if len(last_actions) >= 3 and all(
                last_action == action for last_action in last_actions[-3:]
            ):
                blocked.add(action)

        return blocked

    def _get_oscillation_blocked_actions(
        self,
        recent_steps: List[Dict],
    ) -> Set[str]:
        if len(recent_steps) < 6:
            return set()

        blocked: Set[str] = set()

        last_actions = [item["action"] for item in recent_steps[-6:]]
        last_positions = [item["position"] for item in recent_steps[-6:]]

        unique_positions = set(last_positions)
        is_spatially_stuck = len(unique_positions) <= 2

        if not is_spatially_stuck:
            return blocked

        if (
            last_actions[0] == last_actions[2] == last_actions[4]
            and last_actions[1] == last_actions[3] == last_actions[5]
            and last_actions[0] != last_actions[1]
        ):
            blocked.add(last_actions[1])

        oscillation_pairs = [
            {
                RobotAction.AVANZAR.value,
                RobotAction.RETROCEDER.value,
            },
            {
                RobotAction.GIRAR_IZQUIERDA.value,
                RobotAction.GIRAR_DERECHA.value,
            },
            {
                RobotAction.ESCANEAR.value,
                RobotAction.ENVIAR_ALERTA.value,
            },
            {
                RobotAction.AVANZAR.value,
                RobotAction.VOLVER_BASE.value,
            },
        ]

        recent_pair = set(last_actions[-2:])

        if recent_pair in oscillation_pairs and is_spatially_stuck:
            blocked.update(recent_pair)

        return blocked

    def _get_invalid_actions(
        self,
        state,
        world,
        recent_steps: List[Dict],
        victim_search_mode: bool = False,
    ) -> Set[str]:
        blocked: Set[str] = set()
        current_position = world.current_position()
        robot_is_at_base = current_position == world.base

        if robot_is_at_base and state.battery_level != "BAJA":
            blocked.add(RobotAction.VOLVER_BASE.value)

        if (
            robot_is_at_base
            and state.battery_level in {"ALTA", "MEDIA"}
            and not state.victim_detected
        ):
            blocked.add(RobotAction.ENVIAR_ALERTA.value)
            blocked.add(RobotAction.ESCANEAR.value)

        if (
            not state.victim_detected
            and state.risk_level != "ALTO"
            and state.battery_level != "BAJA"
        ):
            blocked.add(RobotAction.ENVIAR_ALERTA.value)

        last_actions = [item["action"] for item in recent_steps[-3:]]

        if (
            not state.victim_detected
            and last_actions.count(RobotAction.ESCANEAR.value) >= 2
        ):
            blocked.add(RobotAction.ESCANEAR.value)

        if (
            state.battery_level in {"ALTA", "MEDIA"}
            and state.risk_level != "ALTO"
            and not state.victim_detected
            and not victim_search_mode
            and current_position != world.base
        ):
            blocked.add(RobotAction.VOLVER_BASE.value)

        if victim_search_mode and state.battery_level != "BAJA":
            blocked.add(RobotAction.VOLVER_BASE.value)
            blocked.add(RobotAction.ENVIAR_ALERTA.value)

        if state.battery_level == "BAJA":
            blocked.add(RobotAction.ENVIAR_ALERTA.value)

            if not state.victim_detected:
                blocked.add(RobotAction.ESCANEAR.value)

            blocked.discard(RobotAction.VOLVER_BASE.value)

        return blocked

    def _is_stuck(self, recent_steps: List[Dict]) -> bool:
        if len(recent_steps) < 8:
            return False

        last_steps = recent_steps[-8:]
        positions = [item["position"] for item in last_steps]
        actions = [item["action"] for item in last_steps]

        unique_positions = set(positions)
        repeated_area = len(unique_positions) <= 2
        repeated_scans = actions.count(RobotAction.ESCANEAR.value) >= 2

        failed_moves = sum(
            1
            for item in last_steps
            if item["action"]
            in {
                RobotAction.AVANZAR.value,
                RobotAction.RETROCEDER.value,
            }
            and not item["moved"]
        )

        repeated_turns = (
            actions.count(RobotAction.GIRAR_IZQUIERDA.value)
            + actions.count(RobotAction.GIRAR_DERECHA.value)
        ) >= 4

        negative_rewards = sum(
            1
            for item in last_steps
            if item.get("reward", 0) < -20
        )

        return repeated_area and (
            repeated_scans
            or failed_moves >= 2
            or repeated_turns
            or negative_rewards >= 4
        )

    def _choose_escape_action(
        self,
        state,
        recent_steps: List[Dict],
        blocked_actions: Set[str],
    ) -> str:
        last_actions = [item["action"] for item in recent_steps[-4:]]

        if state.obstacle_level == "CERCA":
            if last_actions and last_actions[-1] == RobotAction.GIRAR_DERECHA.value:
                preferred_actions = [
                    RobotAction.GIRAR_IZQUIERDA.value,
                    RobotAction.RETROCEDER.value,
                    RobotAction.GIRAR_DERECHA.value,
                ]
            else:
                preferred_actions = [
                    RobotAction.GIRAR_DERECHA.value,
                    RobotAction.RETROCEDER.value,
                    RobotAction.GIRAR_IZQUIERDA.value,
                ]

        else:
            preferred_actions = [
                RobotAction.AVANZAR.value,
                RobotAction.GIRAR_DERECHA.value,
                RobotAction.GIRAR_IZQUIERDA.value,
                RobotAction.RETROCEDER.value,
            ]

        for action in preferred_actions:
            if action not in blocked_actions:
                return action

        return RobotAction.GIRAR_DERECHA.value

    def _count_repeated_action(
        self,
        recent_steps: List[Dict],
        action: str,
    ) -> int:
        count = 1

        for item in reversed(recent_steps):
            if item["action"] == action:
                count += 1
            else:
                break

        return count

    def _count_same_position(
        self,
        recent_steps: List[Dict],
        position: Position,
    ) -> int:
        count = 1

        for item in reversed(recent_steps):
            if item["position"] == position:
                count += 1
            else:
                break

        return count