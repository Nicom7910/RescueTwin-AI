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

    Lee:
    - /robot/pose
    - /robot/sensor_status
    - /robot/risk_status

    Publica:
    - /robot/cmd_vel
    - /base/alertas
    - /mission/state
    - /mission/current_objective
    - /mission/decision_status
    """

    def __init__(self):
        super().__init__("decision_node")

        # Estado del robot
        self.x = -4.0
        self.y = 0.0
        self.theta = 0.0

        # Últimos datos de sensores
        self.sensor_data: Dict[str, str] = {}
        self.risk_data: Dict[str, str] = {}

        self.mission_state = "EXPLORANDO"
        self.current_wp_index = 0
        self.alert_sent_person = False
        self.alert_count = 0
        self.high_risk_count = 0

        # Ruta lógica del derrumbe
        self.waypoints = [
            {"name": "Entrada del edificio", "x": -3.0, "y": 0.0},
            {"name": "Pasillo principal", "x": -1.0, "y": 0.2},
            {"name": "Zona de escombros inicial", "x": 1.5, "y": 0.8},
            {"name": "Cruce inestable", "x": 3.2, "y": 1.4},
            {"name": "Borde de zona crítica", "x": 4.7, "y": 2.0},
            {"name": "Zona probable de víctima", "x": 6.8, "y": 2.6},
        ]

        # Subscripciones
        self.create_subscription(Odometry, "/robot/pose", self.pose_callback, 10)
        self.create_subscription(String, "/robot/sensor_status", self.sensor_callback, 10)
        self.create_subscription(String, "/robot/risk_status", self.risk_callback, 10)

        # Publishers
        self.cmd_pub = self.create_publisher(Twist, "/robot/cmd_vel", 10)
        self.alert_pub = self.create_publisher(String, "/base/alertas", 10)
        self.state_pub = self.create_publisher(String, "/mission/state", 10)
        self.objective_pub = self.create_publisher(String, "/mission/current_objective", 10)
        self.decision_pub = self.create_publisher(String, "/mission/decision_status", 10)

        # Ciclo de decisión
        self.timer = self.create_timer(2.0, self.decision_loop)

        self.get_logger().info("Decision Node iniciado. Control autónomo activo.")

    # =========================================================
    # Callbacks
    # =========================================================

    def pose_callback(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

        # En motion_node no publicamos orientación como quaternion real.
        # Por eso tomamos theta desde /robot/status si no está disponible.
        self.theta = getattr(self, "theta", 0.0)

    def sensor_callback(self, msg: String):
        self.sensor_data = self.parse_status(msg.data)

    def risk_callback(self, msg: String):
        self.risk_data = self.parse_status(msg.data)

    # =========================================================
    # Utilidades
    # =========================================================

    def parse_status(self, text: str) -> Dict[str, str]:
        """
        Parsea strings tipo:
        Sensores | x=1.2, y=0.4, temp=25.1C, gas=50ppm
        Riesgo IA | nivel=Medio | accion=Avanzar con precaucion
        """
        clean = text.replace(",", " |")
        parts = [p.strip() for p in clean.split("|")]

        data = {"_raw": text}
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            data[key.strip()] = value.strip()

        # Si llega theta por /robot/status en otra versión, lo usamos.
        if "theta" in data:
            self.theta = self.to_float(data.get("theta"), self.theta)

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
            f"estado={self.mission_state} | "
            f"x={self.x:.2f}, y={self.y:.2f} | "
            f"{text}"
        )
        self.publish_string(self.alert_pub, alert)
        self.get_logger().warn(alert)

    def distance_to(self, waypoint: Dict[str, float]) -> float:
        return math.sqrt((waypoint["x"] - self.x) ** 2 + (waypoint["y"] - self.y) ** 2)

    def normalize_angle(self, angle: float) -> float:
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def current_objective(self) -> Dict[str, float]:
        return self.waypoints[min(self.current_wp_index, len(self.waypoints) - 1)]

    def advance_waypoint_if_needed(self):
        wp = self.current_objective()
        if self.distance_to(wp) < 0.9 and self.current_wp_index < len(self.waypoints) - 1:
            self.current_wp_index += 1
            wp_next = self.current_objective()
            self.send_alert(f"Waypoint alcanzado. Nuevo objetivo: {wp_next['name']}")

    # =========================================================
    # Decisión
    # =========================================================

    def compute_navigation_command(self, max_speed: float):
        wp = self.current_objective()

        dx = wp["x"] - self.x
        dy = wp["y"] - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        desired_theta = math.atan2(dy, dx)
        angle_error = self.normalize_angle(desired_theta - self.theta)

        angular = max(-0.9, min(0.9, 1.1 * angle_error))
        linear = min(max_speed, max(0.10, 0.35 * distance))

        # Si está muy desalineado, gira con avance mínimo.
        if abs(angle_error) > 1.0:
            linear = 0.08

        return linear, angular

    def decision_loop(self):
        self.advance_waypoint_if_needed()

        wp = self.current_objective()

        # Valores sensores
        gas = self.to_float(self.sensor_data.get("gas"), 0.0)
        temp = self.to_float(self.sensor_data.get("temp"), 25.0)
        vib = self.to_float(self.sensor_data.get("vib"), 0.0)
        inc = self.to_float(self.sensor_data.get("inc"), 0.0)
        bateria = self.to_float(self.sensor_data.get("bateria"), 100.0)
        obstaculo = self.to_float(self.sensor_data.get("obstaculo"), 5.0)
        persona = int(self.to_float(self.sensor_data.get("persona"), 0.0))

        nivel = self.risk_data.get("nivel", "Desconocido")
        accion_ia = self.risk_data.get("accion", "Sin accion IA")

        decision = ""

        # 1. Víctima detectada
        if persona == 1:
            self.mission_state = "VICTIMA_DETECTADA"
            self.send_cmd(0.0, 0.0)
            decision = "Detenerse y enviar alerta por posible víctima detectada."

            if not self.alert_sent_person:
                self.send_alert(
                    "Posible víctima detectada. "
                    "Se requiere intervención del equipo de rescate."
                )
                self.alert_sent_person = True

        # 2. Batería baja
        elif bateria < 20:
            self.mission_state = "RETORNANDO_BASE"
            self.current_wp_index = 0
            linear, angular = self.compute_navigation_command(max_speed=0.25)
            self.send_cmd(linear, angular)
            decision = "Batería baja. Retornar hacia entrada/base."
            self.send_alert("Batería baja. Robot inicia retorno a base.")

        # 3. Riesgo alto o sensores críticos
        elif nivel == "Alto" or gas > 260 or vib > 1.7 or inc > 25:
            self.mission_state = "EVITANDO_RIESGO"
            self.high_risk_count += 1

            # Maniobra evasiva simple
            angular = 0.85 if self.y <= wp["y"] else -0.85
            self.send_cmd(0.08, angular)

            decision = (
                "Riesgo alto o sensores críticos. "
                "Reducir velocidad, cambiar orientación y evitar zona."
            )

            self.send_alert(
                f"Riesgo alto/sensor crítico. nivel={nivel}, "
                f"gas={gas:.1f}, vib={vib:.2f}, inc={inc:.1f}, temp={temp:.1f}"
            )

            if self.high_risk_count >= 4:
                self.mission_state = "MISION_ABORTADA"
                self.send_cmd(0.0, 0.0)
                decision = "Riesgo alto sostenido. Misión abortada por seguridad."
                self.send_alert("Misión abortada por riesgo alto sostenido.")

        # 4. Obstáculo cercano
        elif obstaculo < 1.0:
            self.mission_state = "EVITANDO_OBSTACULO"
            angular = -0.9 if self.y > 0 else 0.9
            self.send_cmd(0.10, angular)
            decision = "Obstáculo cercano. Ejecutar maniobra evasiva."

        # 5. Riesgo medio
        elif nivel == "Medio" or gas > 150:
            self.mission_state = "EXPLORANDO_CON_PRECAUCION"
            linear, angular = self.compute_navigation_command(max_speed=0.35)
            self.send_cmd(linear, angular)
            decision = "Riesgo medio. Avanzar lentamente hacia objetivo."

        # 6. Riesgo bajo
        else:
            self.mission_state = "EXPLORANDO"
            linear, angular = self.compute_navigation_command(max_speed=0.75)
            self.send_cmd(linear, angular)
            decision = "Riesgo bajo. Continuar exploración hacia waypoint."

        # Fin de ruta sin víctima
        if self.current_wp_index == len(self.waypoints) - 1 and self.distance_to(self.current_objective()) < 0.9:
            if self.mission_state not in ["VICTIMA_DETECTADA", "MISION_ABORTADA"]:
                self.mission_state = "MISION_COMPLETADA"
                self.send_cmd(0.0, 0.0)
                decision = "Último waypoint alcanzado. Misión completada sin nueva alerta."
                self.send_alert("Misión completada. Zona probable inspeccionada.")

        objective_text = (
            f"{wp['name']} | target=({wp['x']:.2f}, {wp['y']:.2f}) | "
            f"robot=({self.x:.2f}, {self.y:.2f})"
        )

        decision_text = (
            f"Decision | state={self.mission_state} | "
            f"objective={wp['name']} | "
            f"risk={nivel} | accion_ia={accion_ia} | "
            f"gas={gas:.1f}ppm | temp={temp:.1f}C | vib={vib:.2f} | "
            f"inc={inc:.1f}deg | bateria={bateria:.1f}% | "
            f"obstaculo={obstaculo:.2f}m | persona={persona} | "
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
