import json
import math
import os
import random
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry
from std_msgs.msg import String


class SensorSimNode(Node):
    """
    Simulador de sensores realista para RescueTwin AI.

    Mejoras:
    - Entorno aleatorio en cada ejecución.
    - Obstáculos aleatorios, pero con una distancia mínima respecto de la entrada.
    - Detección de obstáculos frontal, no 360°, para evitar que el robot quede
      permanentemente en EVITANDO_OBSTACULO por obstáculos laterales o traseros.
    - Víctima probable aleatoria en zona avanzada.
    - Señal de víctima detectable antes para que el robot pueda orientar la búsqueda.
    """

    def __init__(self):
        super().__init__("sensor_sim_node")

        self.x = -3.2
        self.y = 0.0
        self.theta = 0.0
        self.battery = 100.0

        self.map_bounds = {
            "x_min": -3.5,
            "x_max": 7.4,
            "y_min": -3.2,
            "y_max": 3.2,
        }

        seed_env = os.getenv("RESCUETWIN_SEED")

        if seed_env:
            self.seed = int(seed_env)
            random.seed(self.seed)
        else:
            self.seed = random.randint(10000, 99999)
            random.seed(self.seed)

        self.environment = self.generate_random_environment()
        self.save_environment_json()

        self.create_subscription(
            Odometry,
            "/robot/pose",
            self.pose_callback,
            10,
        )

        self.sensor_pub = self.create_publisher(
            String,
            "/robot/sensor_status",
            10,
        )

        self.environment_pub = self.create_publisher(
            String,
            "/mission/environment",
            10,
        )

        self.timer = self.create_timer(1.0, self.publish_sensor_data)

        self.get_logger().info(
            f"Sensor Sim Node iniciado con entorno aleatorio controlado. Seed={self.seed}"
        )

    # =========================================================
    # Generación del entorno
    # =========================================================

    def random_point(self):
        return (
            random.uniform(self.map_bounds["x_min"] + 0.6, self.map_bounds["x_max"] - 0.6),
            random.uniform(self.map_bounds["y_min"] + 0.6, self.map_bounds["y_max"] - 0.6),
        )

    def distance_points(self, a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def is_valid_point(self, point, reserved_points, min_distance=1.25):
        entry = (-3.2, 0.0)

        # Evita bloquear la salida inicial.
        if self.distance_points(point, entry) < 1.8:
            return False

        for reserved in reserved_points:
            if self.distance_points(point, reserved) < min_distance:
                return False

        return True

    def generate_random_environment(self):
        entrada = (-3.2, 0.0)

        # Víctima en zona avanzada, pero no siempre pegada al extremo.
        victim = (
            random.uniform(4.7, 6.9),
            random.uniform(-2.2, 2.3),
        )

        reserved = [entrada, victim]

        obstacles = []

        # Menos obstáculos que antes para que el mapa sea desafiante pero recorrible.
        for i in range(random.randint(4, 6)):
            for _ in range(120):
                point = self.random_point()

                if self.is_valid_point(point, reserved, min_distance=1.25):
                    radius = random.uniform(0.30, 0.62)

                    obstacles.append(
                        {
                            "name": f"Obstáculo aleatorio {i + 1}",
                            "x": round(point[0], 2),
                            "y": round(point[1], 2),
                            "radius": round(radius, 2),
                            "type": random.choice(
                                [
                                    "escombros",
                                    "columna caída",
                                    "pared derrumbada",
                                    "estructura inestable",
                                ]
                            ),
                        }
                    )

                    reserved.append(point)
                    break

        risk_zones = []

        for i in range(random.randint(3, 5)):
            for _ in range(120):
                point = self.random_point()

                if self.is_valid_point(point, reserved, min_distance=1.1):
                    risk_level = random.choice(["medio", "medio", "alto"])
                    radius = random.uniform(0.75, 1.2)

                    risk_zones.append(
                        {
                            "name": f"Zona de riesgo {i + 1}",
                            "x": round(point[0], 2),
                            "y": round(point[1], 2),
                            "radius": round(radius, 2),
                            "risk_level": risk_level,
                        }
                    )

                    reserved.append(point)
                    break

        return {
            "seed": self.seed,
            "created_at": datetime.now().isoformat(),
            "map_bounds": self.map_bounds,
            "entry": {
                "name": "Entrada",
                "x": entrada[0],
                "y": entrada[1],
            },
            "victim": {
                "name": "Víctima probable",
                "x": round(victim[0], 2),
                "y": round(victim[1], 2),
                "detection_radius": 1.00,
                "signal_radius": 4.2,
            },
            "obstacles": obstacles,
            "risk_zones": risk_zones,
        }

    def find_project_dir(self) -> Path:
        current = Path.cwd().resolve()

        for path in [current] + list(current.parents):
            if (path / "reports").exists() or (path / "run_rescuetwin_full_project.py").exists():
                return path

        return current

    def save_environment_json(self):
        project_dir = self.find_project_dir()
        log_dir = project_dir / "reports" / "mission_logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        latest_path = log_dir / "latest_environment.json"
        timestamp_path = log_dir / f"environment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        for path in [latest_path, timestamp_path]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.environment, f, ensure_ascii=False, indent=4)

    # =========================================================
    # Sensores
    # =========================================================

    def pose_callback(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w

        self.theta = math.atan2(2.0 * qw * qz, 1.0 - 2.0 * qz * qz)

    def normalize_angle(self, angle: float):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi

        return angle

    def distance_to_xy(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def clamp(self, value: float, min_value: float, max_value: float):
        return max(min_value, min(value, max_value))

    def front_obstacle_distance(self):
        """
        Simula sensor frontal.
        Solo detecta obstáculos que estén delante del robot y dentro de un cono.
        Esto evita que un obstáculo lateral/trasero bloquee toda la misión.
        """

        min_distance = 5.0
        nearest_type = "ninguno"

        sensor_cone_rad = math.radians(80)

        for obstacle in self.environment["obstacles"]:
            dx = obstacle["x"] - self.x
            dy = obstacle["y"] - self.y

            distance_center = math.sqrt(dx * dx + dy * dy)
            distance_surface = distance_center - obstacle["radius"]

            angle_to_obstacle = math.atan2(dy, dx)
            angle_error = abs(self.normalize_angle(angle_to_obstacle - self.theta))

            # Obstáculo frontal solamente.
            if angle_error <= sensor_cone_rad / 2.0 and distance_surface < min_distance:
                min_distance = distance_surface
                nearest_type = obstacle["type"]

        return self.clamp(min_distance, 0.15, 5.0), nearest_type

    def risk_effects(self):
        gas_extra = 0.0
        temp_extra = 0.0
        vib_extra = 0.0
        inc_extra = 0.0
        current_risk = "bajo"
        nearest_risk = "ninguna"

        for zone in self.environment["risk_zones"]:
            distance = self.distance_to_xy(zone["x"], zone["y"])

            if distance < zone["radius"]:
                intensity = 1.0 - distance / zone["radius"]

                if zone["risk_level"] == "alto":
                    gas_extra += 135.0 * intensity
                    temp_extra += 5.2 * intensity
                    vib_extra += 0.75 * intensity
                    inc_extra += 8.0 * intensity
                    current_risk = "alto"
                else:
                    gas_extra += 70.0 * intensity
                    temp_extra += 3.0 * intensity
                    vib_extra += 0.38 * intensity
                    inc_extra += 4.0 * intensity

                    if current_risk != "alto":
                        current_risk = "medio"

                nearest_risk = zone["name"]

        return gas_extra, temp_extra, vib_extra, inc_extra, current_risk, nearest_risk

    def victim_signal(self):
        victim = self.environment["victim"]

        distance = self.distance_to_xy(victim["x"], victim["y"])
        signal_radius = victim["signal_radius"]
        detection_radius = victim["detection_radius"]

        person_detected = 1 if distance <= detection_radius else 0

        if distance <= signal_radius:
            signal_strength = 1.0 - distance / signal_radius

            angle_to_victim = math.atan2(victim["y"] - self.y, victim["x"] - self.x)
            bearing = self.normalize_angle(angle_to_victim - self.theta)
        else:
            signal_strength = 0.0
            bearing = 0.0

        return person_detected, signal_strength, bearing, distance

    def publish_sensor_data(self):
        obstacle_distance, obstacle_type = self.front_obstacle_distance()
        gas_extra, temp_extra, vib_extra, inc_extra, local_risk, risk_zone = self.risk_effects()
        person_detected, victim_signal, victim_bearing, victim_distance = self.victim_signal()

        temperature = 24.0 + temp_extra + random.normalvariate(0.0, 1.0)
        gas_ppm = 60.0 + gas_extra + random.normalvariate(0.0, 7.0)
        vibration = 0.22 + vib_extra + random.normalvariate(0.0, 0.05)
        inclination = 4.0 + inc_extra + random.normalvariate(0.0, 1.0)
        obstacle_distance = obstacle_distance + random.normalvariate(0.0, 0.06)

        if obstacle_distance < 0.75:
            vibration += 0.12
            inclination += 1.4

        self.battery -= random.uniform(0.06, 0.16)
        self.battery = self.clamp(self.battery, 5.0, 100.0)

        temperature = self.clamp(temperature, 10.0, 65.0)
        gas_ppm = self.clamp(gas_ppm, 20.0, 450.0)
        vibration = self.clamp(vibration, 0.0, 3.2)
        inclination = self.clamp(inclination, 0.0, 42.0)
        obstacle_distance = self.clamp(obstacle_distance, 0.15, 5.0)
        victim_signal = self.clamp(victim_signal, 0.0, 1.0)

        msg = String()
        msg.data = (
            f"Sensores | "
            f"x={self.x:.2f}, y={self.y:.2f}, theta={self.theta:.2f}, "
            f"temp={temperature:.1f}C, "
            f"gas={gas_ppm:.1f}ppm, "
            f"vib={vibration:.2f}, "
            f"inc={inclination:.1f}, "
            f"bateria={self.battery:.1f}, "
            f"obstaculo={obstacle_distance:.2f}, "
            f"tipo_obstaculo={obstacle_type}, "
            f"riesgo_local={local_risk}, "
            f"zona_riesgo={risk_zone}, "
            f"persona={person_detected}, "
            f"victim_signal={victim_signal:.2f}, "
            f"victim_bearing={victim_bearing:.2f}, "
            f"victim_distance={victim_distance:.2f}"
        )

        env_msg = String()
        env_msg.data = json.dumps(self.environment, ensure_ascii=False)

        self.sensor_pub.publish(msg)
        self.environment_pub.publish(env_msg)


def main(args=None):
    rclpy.init(args=args)
    node = SensorSimNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()