import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from collections import deque

from app.autonomous.actions import RobotAction
from app.autonomous.state import RobotPose, SensorReading


Position = Tuple[int, int]


@dataclass
class StepResult:
    collided: bool
    reached_victim: bool
    returned_base: bool
    moved: bool
    message: str

class ProceduralWorld:
    """
    Mundo procedural para RescueTwin.

    No carga escenarios desde archivos.
    En cada misión genera un entorno diferente con:
    - obstáculos
    - gas
    - temperatura
    - inestabilidad estructural
    - víctimas
    - ruido de sensores

    El robot no conoce el mapa real. Solo percibe mediante sensores.
    """

    DIRECTIONS = ["N", "E", "S", "W"]

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        seed: Optional[int] = None,
        obstacle_density: Optional[float] = None,
        hazard_density: Optional[float] = None,
        victim_count: Optional[int] = None,
    ):
        self.width = width
        self.height = height
        self.random = random.Random(seed)
        self.seed = seed

        self.obstacle_density = obstacle_density if obstacle_density is not None else self.random.uniform(0.08, 0.18)
        self.hazard_density = hazard_density if hazard_density is not None else self.random.uniform(0.10, 0.25)
        self.victim_count = victim_count if victim_count is not None else self.random.randint(1, 4)

        self.base: Position = (width // 2, height // 2)
        self.pose = RobotPose(x=self.base[0], y=self.base[1], direction=self.random.choice(self.DIRECTIONS))
        self.battery = 100.0

        self.obstacles: Set[Position] = set()
        self.victims: Set[Position] = set()
        self.gas_map: Dict[Position, float] = {}
        self.temperature_map: Dict[Position, float] = {}
        self.vibration_map: Dict[Position, float] = {}
        self.inclination_map: Dict[Position, float] = {}
        self.visited: Set[Position] = {self.base}

        self._generate_world()

    def _generate_world(self) -> None:
        total_cells = self.width * self.height

        obstacle_target = int(total_cells * self.obstacle_density)
        hazard_target = int(total_cells * self.hazard_density)

        while len(self.obstacles) < obstacle_target:
            pos = self._random_position()
            if pos != self.base:
                self.obstacles.add(pos)

        while len(self.victims) < self.victim_count:
            pos = self._random_position()
            if pos != self.base and pos not in self.obstacles:
                self.victims.add(pos)

        for _ in range(hazard_target):
            pos = self._random_position()
            if pos not in self.obstacles:
                self.gas_map[pos] = self.random.uniform(80, 280)

        for _ in range(hazard_target):
            pos = self._random_position()
            if pos not in self.obstacles:
                self.temperature_map[pos] = self.random.uniform(28, 55)

        for _ in range(hazard_target):
            pos = self._random_position()
            if pos not in self.obstacles:
                self.vibration_map[pos] = self.random.uniform(0.35, 1.0)

        for _ in range(hazard_target):
            pos = self._random_position()
            if pos not in self.obstacles:
                self.inclination_map[pos] = self.random.uniform(6, 24)

    def _random_position(self) -> Position:
        return self.random.randint(0, self.width - 1), self.random.randint(0, self.height - 1)

    def current_position(self) -> Position:
        return self.pose.x, self.pose.y

    def in_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def front_position(self) -> Position:
        return self._next_position(self.pose.direction)

    def back_position(self) -> Position:
        opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}[self.pose.direction]
        return self._next_position(opposite)

    def _next_position(self, direction: str) -> Position:
        x, y = self.current_position()
        if direction == "N":
            return x, y - 1
        if direction == "S":
            return x, y + 1
        if direction == "E":
            return x + 1, y
        if direction == "W":
            return x - 1, y
        raise ValueError(f"Dirección inválida: {direction}")

    def _rotate_left(self) -> None:
        idx = self.DIRECTIONS.index(self.pose.direction)
        self.pose.direction = self.DIRECTIONS[(idx - 1) % len(self.DIRECTIONS)]

    def _rotate_right(self) -> None:
        idx = self.DIRECTIONS.index(self.pose.direction)
        self.pose.direction = self.DIRECTIONS[(idx + 1) % len(self.DIRECTIONS)]

    def read_sensors(self) -> SensorReading:
        pos = self.current_position()

        temperature = self.temperature_map.get(pos, self.random.uniform(20, 29))
        gas = self.gas_map.get(pos, self.random.uniform(20, 75))
        vibration = self.vibration_map.get(pos, self.random.uniform(0.05, 0.35))
        inclination = self.inclination_map.get(pos, self.random.uniform(0, 8))
        obstacle_distance = self._estimate_obstacle_distance()
        victim_signal = self._estimate_victim_signal()

        return SensorReading(
            temperature=max(0, temperature + self.random.gauss(0, 1.6)),
            gas=max(0, gas + self.random.gauss(0, 8)),
            vibration=max(0, min(1.5, vibration + self.random.gauss(0, 0.04))),
            inclination=max(0, inclination + self.random.gauss(0, 0.6)),
            battery=max(0, self.battery + self.random.gauss(0, 0.4)),
            obstacle_distance=max(0.1, obstacle_distance + self.random.gauss(0, 0.15)),
            victim_signal=max(0, min(1, victim_signal + self.random.gauss(0, 0.06))),
        )

    def _estimate_obstacle_distance(self, max_distance: int = 5) -> float:
        for dist in range(1, max_distance + 1):
            probe = self._position_ahead(dist)
            if not self.in_bounds(probe) or probe in self.obstacles:
                return float(dist)
        return float(max_distance)

    def _position_ahead(self, distance: int) -> Position:
        x, y = self.current_position()
        if self.pose.direction == "N":
            return x, y - distance
        if self.pose.direction == "S":
            return x, y + distance
        if self.pose.direction == "E":
            return x + distance, y
        if self.pose.direction == "W":
            return x - distance, y
        return x, y

    def _estimate_victim_signal(self) -> float:
        if not self.victims:
            return 0.0

        x, y = self.current_position()
        distances = [abs(x - vx) + abs(y - vy) for vx, vy in self.victims]
        nearest = min(distances)

        if nearest == 0:
            return 1.0

        return max(0.0, 1.0 - nearest / 8.0)

    def apply_action(self, action: str) -> StepResult:
        action = RobotAction(action)
        if not (action == RobotAction.VOLVER_BASE and self.current_position() == self.base):
            self.battery = max(0, self.battery - self._battery_cost(action))

        collided = False
        moved = False
        reached_victim = False
        returned_base = False
        message = "Acción ejecutada"

        if action == RobotAction.GIRAR_IZQUIERDA:
            self._rotate_left()
            message = "El robot giró a la izquierda"

        elif action == RobotAction.GIRAR_DERECHA:
            self._rotate_right()
            message = "El robot giró a la derecha"

        elif action == RobotAction.AVANZAR:
            collided, moved = self._move_to(self.front_position())
            message = "El robot avanzó" if moved else "El robot no pudo avanzar"

        elif action == RobotAction.RETROCEDER:
            collided, moved = self._move_to(self.back_position())
            message = "El robot retrocedió" if moved else "El robot no pudo retroceder"

        elif action == RobotAction.ESCANEAR:
            message = "El robot escaneó el entorno cercano"

        elif action == RobotAction.ENVIAR_ALERTA:
            message = "El robot envió una alerta a la base"

        elif action == RobotAction.VOLVER_BASE:
            moved = self._move_towards_base()
            returned_base = self.current_position() == self.base

            if returned_base:
                message = "El robot volvió a la base"
            elif moved:
                message = "El robot avanza por ruta calculada hacia la base"
            else:
                message = "No se encontró ruta segura hacia la base"

        self.visited.add(self.current_position())

        if self.current_position() in self.victims:
            reached_victim = True
            self.victims.remove(self.current_position())
            message = "El robot encontró una posible víctima"

        if self.current_position() == self.base and action == RobotAction.VOLVER_BASE:
            returned_base = True

        return StepResult(
            collided=collided,
            reached_victim=reached_victim,
            returned_base=returned_base,
            moved=moved,
            message=message,
        )

    def _battery_cost(self, action: RobotAction) -> float:
        costs = {
            RobotAction.AVANZAR: 1.2,
            RobotAction.RETROCEDER: 1.0,
            RobotAction.GIRAR_IZQUIERDA: 0.5,
            RobotAction.GIRAR_DERECHA: 0.5,
            RobotAction.ESCANEAR: 0.8,
            RobotAction.ENVIAR_ALERTA: 0.3,
            RobotAction.VOLVER_BASE: 1.1,
        }
        return costs[action] + self.random.uniform(0, 0.4)

    def _move_to(self, pos: Position) -> Tuple[bool, bool]:
        if not self.in_bounds(pos) or pos in self.obstacles:
            return True, False

        self.pose.x, self.pose.y = pos
        return False, True

    def _move_towards_base(self) -> bool:
        """
        Mueve al robot un paso hacia la base usando BFS.

        Antes el robot intentaba volver en línea recta.
        Eso podía dejarlo atrapado cuando había obstáculos.

        Ahora calcula una ruta por grilla evitando obstáculos.
        """

        current = self.current_position()

        if current == self.base:
            return True

        path = self._find_path_bfs(start=current, goal=self.base)

        if not path or len(path) < 2:
            return False

        next_position = path[1]

        if not self.in_bounds(next_position) or next_position in self.obstacles:
            return False

        self.pose.x, self.pose.y = next_position
        return True

    def _find_path_bfs(self, start: Position, goal: Position):
        """
        Busca un camino desde start hasta goal usando BFS.

        Devuelve una lista de posiciones:
        [start, paso_1, paso_2, ..., goal]

        Si no encuentra camino, devuelve None.
        """

        if start == goal:
            return [start]

        queue = deque([start])
        came_from = {start: None}

        while queue:
            current = queue.popleft()

            if current == goal:
                break

            for neighbor in self._get_neighbors(current):
                if neighbor in came_from:
                    continue

                if not self.in_bounds(neighbor):
                    continue

                if neighbor in self.obstacles:
                    continue

                came_from[neighbor] = current
                queue.append(neighbor)

        if goal not in came_from:
            return None

        path = []
        current = goal

        while current is not None:
            path.append(current)
            current = came_from[current]

        path.reverse()
        return path


    def _get_neighbors(self, position: Position):
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
            if self.in_bounds(candidate) and candidate not in self.obstacles
        ]

    def visited_ratio(self) -> float:
        traversable = self.width * self.height - len(self.obstacles)
        return len(self.visited) / max(1, traversable)

    def remaining_victims(self) -> int:
        return len(self.victims)

    def render_ascii(self, reveal_world: bool = False) -> str:
        lines = []
        robot_pos = self.current_position()

        for y in range(self.height):
            row = []
            for x in range(self.width):
                pos = (x, y)

                if pos == robot_pos:
                    row.append("R")
                elif pos == self.base:
                    row.append("B")
                elif reveal_world and pos in self.obstacles:
                    row.append("#")
                elif reveal_world and pos in self.victims:
                    row.append("V")
                elif pos in self.visited:
                    row.append(".")
                else:
                    row.append("?")
            lines.append("".join(row))

        return "\n".join(lines)
