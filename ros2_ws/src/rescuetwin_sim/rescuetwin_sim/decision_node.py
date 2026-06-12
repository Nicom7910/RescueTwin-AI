import math
import re
from typing import Dict, Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


class DecisionNode(Node):
    """
    Nodo de decisión autónoma para RescueTwin AI.

    Funciones:
    - Explora el entorno por sectores.
    - Reacciona ante obstáculos, riesgo y batería.
    - Prioriza señal de víctima cuando aparece.
    - Detiene el robot ante víctima confirmada.
    - Publica objetivo actual coherente con el estado real.
    - Republica alertas críticas para que el logger/snapshot las capture.
    """

    def __init__(self):
        super().__init__("decision_node")

        self.x = -3.2
        self.y = 0.0
        self.theta = 0.0

        self.sensor_data: Dict[str, str] = {}
        self.risk_data: Dict[str, str] = {}

        self.mission_state = "INICIANDO_EXPLORACION"

        self.map_bounds = {
            "x_min": -3.5,
            "x_max": 7.4,
            "y_min": -3.2,
            "y_max": 3.2,
        }

        self.grid_size = 0.8
        self.visited_cells = set()

        self.exploration_waypoints = self.generate_exploration_waypoints()
        self.current_wp_index = 0

        self.avoidance_ticks = 0
        self.high_risk_ticks = 0
        self.extreme_risk_ticks = 0
        self.recovery_ticks = 0

        self.alert_count = 0
        self.victim_alert_sent = False
        self.mission_complete_sent = False

        self.last_alert_text = ""
        self.last_positions = []

        self.create_subscription(Odometry, "/robot/pose", self.pose_callback, 10)
        self.create_subscription(String, "/robot/sensor_status", self.sensor_callback, 10)
        self.create_subscription(String, "/robot/risk_status", self.risk_callback, 10)

        self.cmd_pub = self.create_publisher(Twist, "/robot/cmd_vel", 10)
        self.alert_pub = self.create_publisher(String, "/base/alertas", 10)
        self.state_pub = self.create_publisher(String, "/mission/state", 10)
        self.objective_pub = self.create_publisher(String, "/mission/current_objective", 10)
        self.decision_pub = self.create_publisher(String, "/mission/decision_status", 10)

        self.timer = self.create_timer(1.0, self.decision_loop)

        self.get_logger().info("Decision Node iniciado con exploración mejorada.")

    # =========================================================
    # Callbacks
    # =========================================================

    def pose_callback(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w

        self.theta = math.atan2(2.0 * qw * qz, 1.0 - 2.0 * qz * qz)

    def sensor_callback(self, msg: String):
        self.sensor_data = self.parse_status(msg.data)

    def risk_callback(self, msg: String):
        self.risk_data = self.parse_status(msg.data)

    # =========================================================
    # Utilidades
    # =========================================================

    def parse_status(self, text: str) -> Dict[str, str]:
        clean = text.replace(",", " |")
        parts = [p.strip() for p in clean.split("|")]

        data = {"_raw": text}

        for part in parts:
            if "=" not in part:
                continue

            key, value = part.split("=", 1)
            data[key.strip()] = value.strip()

        return data

    def to_float(self, value: Optional[str], default: float = 0.0) -> float:
        if value is None:
            return default

        match = re.search(r"-?\d+(\.\d+)?", str(value))

        if match is None:
            return default

        return float(match.group(0))

    def publish_string(self, publisher, text: str):
        msg = String()
        msg.data = text
        publisher.publish(msg)

    def send_cmd(self, linear: float, angular: float):
        msg = Twist()
        msg.linear.x = float(linear)
        msg.angular.z = float(angular)
        self.cmd_pub.publish(msg)

    def send_alert(self, text: str):
        self.alert_count += 1

        alert = (
            f"ALERTA BASE #{self.alert_count} | "
            f"state={self.mission_state} | "
            f"x={self.x:.2f}, y={self.y:.2f} | "
            f"{text}"
        )

        self.last_alert_text = alert
        self.publish_string(self.alert_pub, alert)
        self.get_logger().warn(alert)

    def republish_last_alert(self):
        """
        ROS no retiene automáticamente el último mensaje para nuevos lectores.
        Por eso, mientras la misión esté en un estado crítico, republicamos
        la última alerta para que el logger y los snapshots la capturen.
        """

        if self.last_alert_text:
            self.publish_string(self.alert_pub, self.last_alert_text)

    def normalize_angle(self, angle: float):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi

        return angle

    def current_cell(self):
        gx = int((self.x - self.map_bounds["x_min"]) / self.grid_size)
        gy = int((self.y - self.map_bounds["y_min"]) / self.grid_size)

        return gx, gy

    def update_visited_cells(self):
        self.visited_cells.add(self.current_cell())

    def exploration_percent(self):
        x_cells = int((self.map_bounds["x_max"] - self.map_bounds["x_min"]) / self.grid_size)
        y_cells = int((self.map_bounds["y_max"] - self.map_bounds["y_min"]) / self.grid_size)

        total_cells = max(1, x_cells * y_cells)

        return min(100.0, len(self.visited_cells) / total_cells * 100.0)

    def distance_to_point(self, px: float, py: float):
        return math.sqrt((px - self.x) ** 2 + (py - self.y) ** 2)

    def generate_exploration_waypoints(self):
        waypoints = []

        columns = [
            (-2.6, [-0.8, 0.0, 0.8]),
            (-1.4, [1.4, 0.0, -1.4]),
            (-0.2, [-2.0, -0.8, 0.8, 2.0]),
            (1.0, [2.2, 1.0, -0.4, -1.8]),
            (2.2, [-2.2, -1.0, 0.4, 1.8]),
            (3.4, [2.2, 0.8, -0.8, -2.2]),
            (4.6, [-2.0, -0.6, 0.8, 2.0]),
            (5.8, [2.2, 1.0, -0.4, -1.8]),
            (6.8, [-1.5, 0.0, 1.5]),
        ]

        for x, y_values in columns:
            for y in y_values:
                waypoints.append(
                    {
                        "name": f"Sector x={x:.1f}, y={y:.1f}",
                        "x": x,
                        "y": y,
                    }
                )

        return waypoints

    def current_waypoint(self):
        if self.current_wp_index >= len(self.exploration_waypoints):
            return self.exploration_waypoints[-1]

        return self.exploration_waypoints[self.current_wp_index]

    def advance_waypoint(self):
        if self.current_wp_index < len(self.exploration_waypoints) - 1:
            self.current_wp_index += 1

    def skip_current_sector(self, reason: str):
        wp = self.current_waypoint()

        self.send_alert(
            f"Sector omitido por {reason}. "
            f"sector=({wp['x']:.2f}, {wp['y']:.2f})"
        )

        self.advance_waypoint()

    def navigation_command_to_point(self, target_x: float, target_y: float, max_speed: float):
        dx = target_x - self.x
        dy = target_y - self.y

        distance = math.sqrt(dx * dx + dy * dy)

        desired_theta = math.atan2(dy, dx)
        angle_error = self.normalize_angle(desired_theta - self.theta)

        angular = max(-1.2, min(1.2, 1.7 * angle_error))

        linear = min(max_speed, max(0.10, 0.48 * distance))

        if abs(angle_error) > 1.2:
            linear = 0.05

        return linear, angular, distance, angle_error

    def avoidance_command(self):
        if self.avoidance_ticks <= 3:
            return -0.08, 0.55

        if self.avoidance_ticks <= 7:
            return 0.20, 0.65

        return 0.26, -0.45

    def update_position_history(self):
        self.last_positions.append((self.x, self.y))

        if len(self.last_positions) > 14:
            self.last_positions.pop(0)

    def is_stuck(self):
        if len(self.last_positions) < 14:
            return False

        first = self.last_positions[0]
        last = self.last_positions[-1]

        displacement = math.sqrt((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2)

        return displacement < 0.45

    def build_objective_text(self, explored: float, victim_signal: float):
        """
        Corrige el punto del objetivo desactualizado.
        Si la víctima fue detectada, ya no se informa el sector viejo,
        sino el objetivo real de la misión.
        """

        if self.mission_state == "VICTIMA_DETECTADA":
            return (
                f"Objetivo | VICTIMA_DETECTADA | "
                f"robot=({self.x:.2f}, {self.y:.2f}) | "
                f"explorado={explored:.1f}% | "
                f"victim_signal={victim_signal:.2f} | "
                f"accion=Robot detenido. Enviar equipo de rescate."
            )

        if self.mission_state == "SIGUIENDO_SENAL_DE_VICTIMA":
            return (
                f"Objetivo | SIGUIENDO_SENAL_DE_VICTIMA | "
                f"robot=({self.x:.2f}, {self.y:.2f}) | "
                f"explorado={explored:.1f}% | "
                f"victim_signal={victim_signal:.2f} | "
                f"accion=Aproximacion controlada hacia señal."
            )

        wp = self.current_waypoint()

        return (
            f"Objetivo | "
            f"sector={self.current_wp_index + 1}/{len(self.exploration_waypoints)} | "
            f"target=({wp['x']:.2f}, {wp['y']:.2f}) | "
            f"robot=({self.x:.2f}, {self.y:.2f}) | "
            f"explorado={explored:.1f}%"
        )

    # =========================================================
    # Loop principal
    # =========================================================

    def decision_loop(self):
        self.update_visited_cells()
        self.update_position_history()

        gas = self.to_float(self.sensor_data.get("gas"), 0.0)
        temp = self.to_float(self.sensor_data.get("temp"), 25.0)
        vib = self.to_float(self.sensor_data.get("vib"), 0.0)
        inc = self.to_float(self.sensor_data.get("inc"), 0.0)
        bateria = self.to_float(self.sensor_data.get("bateria"), 100.0)
        obstaculo = self.to_float(self.sensor_data.get("obstaculo"), 5.0)
        persona = int(self.to_float(self.sensor_data.get("persona"), 0.0))
        victim_signal = self.to_float(self.sensor_data.get("victim_signal"), 0.0)
        victim_bearing = self.to_float(self.sensor_data.get("victim_bearing"), 0.0)

        riesgo_local = self.sensor_data.get("riesgo_local", "bajo")
        tipo_obstaculo = self.sensor_data.get("tipo_obstaculo", "desconocido")

        nivel_modelo = self.risk_data.get("nivel", "Desconocido")
        accion_ia = self.risk_data.get("accion", "Sin accion IA")

        risk_extreme = gas > 360 or temp > 55 or vib > 2.5 or inc > 36
        risk_high = (
            riesgo_local == "alto"
            or nivel_modelo == "Alto"
            or gas > 270
            or vib > 1.8
            or inc > 27
        )
        risk_medium = (
            riesgo_local == "medio"
            or nivel_modelo == "Medio"
            or gas > 165
            or vib > 1.0
            or inc > 16
        )

        decision = ""

        if persona == 1:
            self.mission_state = "VICTIMA_DETECTADA"
            self.send_cmd(0.0, 0.0)

            decision = (
                "Víctima probable confirmada por sensores. "
                "Robot detenido y alerta enviada a la base."
            )

            if not self.victim_alert_sent:
                self.send_alert(
                    "Víctima probable detectada. "
                    "Enviar equipo de rescate a la ubicación estimada."
                )
                self.victim_alert_sent = True
            else:
                self.republish_last_alert()

        elif victim_signal > 0.18 and obstaculo > 0.38 and not risk_extreme:
            self.mission_state = "SIGUIENDO_SENAL_DE_VICTIMA"
            self.avoidance_ticks = 0
            self.high_risk_ticks = 0
            self.extreme_risk_ticks = 0

            desired_theta = self.normalize_angle(self.theta + victim_bearing)
            target_x = self.x + math.cos(desired_theta) * 1.2
            target_y = self.y + math.sin(desired_theta) * 1.2

            linear, angular, _, _ = self.navigation_command_to_point(
                target_x,
                target_y,
                max_speed=0.42,
            )

            self.send_cmd(linear, angular)

            decision = (
                "Señal de víctima detectada. "
                "Se prioriza aproximación controlada hacia la señal."
            )

        elif bateria < 12:
            self.mission_state = "RETORNANDO_BASE"

            linear, angular, _, _ = self.navigation_command_to_point(
                -3.2,
                0.0,
                max_speed=0.36,
            )

            self.send_cmd(linear, angular)

            decision = "Batería crítica. Retorno a entrada/base."

        elif self.is_stuck():
            self.recovery_ticks += 1
            self.mission_state = "RECUPERACION_POR_ESTANCAMIENTO"

            self.send_cmd(-0.10, -0.85)

            decision = "El robot detectó bajo avance real. Ejecuta recuperación."

            if self.recovery_ticks >= 4:
                self.skip_current_sector("estancamiento")
                self.last_positions = []
                self.recovery_ticks = 0
                self.avoidance_ticks = 0

        elif risk_extreme:
            self.extreme_risk_ticks += 1
            self.mission_state = "EVITANDO_RIESGO_EXTREMO"

            self.send_cmd(0.12, 0.75)

            decision = "Riesgo extremo. Maniobra evasiva y salida del sector."

            if self.extreme_risk_ticks in [1, 4]:
                self.send_alert(
                    f"Riesgo extremo. gas={gas:.1f}, temp={temp:.1f}, "
                    f"vib={vib:.2f}, inc={inc:.1f}."
                )

            if self.extreme_risk_ticks >= 5:
                self.skip_current_sector("riesgo extremo persistente")
                self.extreme_risk_ticks = 0

        elif obstaculo < 0.42:
            self.avoidance_ticks += 1
            self.mission_state = "EVITANDO_OBSTACULO"

            linear, angular = self.avoidance_command()
            self.send_cmd(linear, angular)

            decision = (
                f"Obstáculo frontal cercano detectado ({tipo_obstaculo}). "
                "Evasión corta y controlada."
            )

            if self.avoidance_ticks in [1, 5]:
                self.send_alert(
                    f"Obstáculo frontal detectado: {tipo_obstaculo}. "
                    f"distancia={obstaculo:.2f}m."
                )

            if self.avoidance_ticks >= 9:
                self.skip_current_sector("obstáculo persistente")
                self.avoidance_ticks = 0

        elif risk_high:
            self.high_risk_ticks += 1
            self.mission_state = "RODEANDO_ZONA_DE_RIESGO"

            self.send_cmd(0.20, 0.55)

            decision = "Riesgo alto. Rodea zona y continúa exploración."

            if self.high_risk_ticks in [1, 5]:
                self.send_alert(
                    f"Riesgo alto detectado. gas={gas:.1f}, temp={temp:.1f}, "
                    f"vib={vib:.2f}, inc={inc:.1f}."
                )

            if self.high_risk_ticks >= 7:
                self.skip_current_sector("riesgo alto persistente")
                self.high_risk_ticks = 0

        elif risk_medium:
            self.avoidance_ticks = 0
            self.extreme_risk_ticks = 0
            self.high_risk_ticks = max(0, self.high_risk_ticks - 1)

            self.mission_state = "EXPLORANDO_CON_PRECAUCION"

            wp = self.current_waypoint()

            linear, angular, distance, _ = self.navigation_command_to_point(
                wp["x"],
                wp["y"],
                max_speed=0.36,
            )

            self.send_cmd(linear, angular)

            decision = "Riesgo medio. Avance con precaución."

            if distance < 0.55:
                self.advance_waypoint()

        else:
            self.avoidance_ticks = 0
            self.extreme_risk_ticks = 0
            self.high_risk_ticks = max(0, self.high_risk_ticks - 1)
            self.recovery_ticks = 0

            self.mission_state = "EXPLORANDO_SECTORES"

            wp = self.current_waypoint()

            linear, angular, distance, _ = self.navigation_command_to_point(
                wp["x"],
                wp["y"],
                max_speed=0.62,
            )

            self.send_cmd(linear, angular)

            decision = "Riesgo bajo. Exploración por sectores hacia zona avanzada."

            if distance < 0.60:
                self.advance_waypoint()

        if (
            self.current_wp_index >= len(self.exploration_waypoints) - 1
            and self.mission_state not in ["VICTIMA_DETECTADA", "RETORNANDO_BASE"]
        ):
            self.mission_state = "EXPLORACION_COMPLETA_SIN_DETECCION"

            if not self.mission_complete_sent:
                self.send_alert("Exploración completada sin detección directa de víctima.")
                self.mission_complete_sent = True

        explored = self.exploration_percent()

        objective_text = self.build_objective_text(
            explored=explored,
            victim_signal=victim_signal,
        )

        decision_text = (
            f"Decision | "
            f"state={self.mission_state} | "
            f"x={self.x:.2f} | y={self.y:.2f} | "
            f"risk={nivel_modelo} | riesgo_local={riesgo_local} | "
            f"accion_ia={accion_ia} | "
            f"gas={gas:.1f}ppm | temp={temp:.1f}C | vib={vib:.2f} | "
            f"inc={inc:.1f}deg | bateria={bateria:.1f}% | "
            f"obstaculo={obstaculo:.2f}m | "
            f"persona={persona} | "
            f"victim_signal={victim_signal:.2f} | "
            f"victim_bearing={victim_bearing:.2f} | "
            f"explorado={explored:.1f}% | "
            f"decision={decision}"
        )

        self.publish_string(self.state_pub, self.mission_state)
        self.publish_string(self.objective_pub, objective_text)
        self.publish_string(self.decision_pub, decision_text)


def main(args=None):
    rclpy.init(args=args)
    node = DecisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()