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

    Mejora principal:
    - El robot ahora tiene una misión orientada a objetivo.
    - Recorre una ruta extendida hasta la víctima probable.
    - Ante riesgo alto, no aborta inmediatamente: rodea la zona crítica.
    - Solo aborta si el riesgo extremo se sostiene durante demasiado tiempo.
    """

    def __init__(self):
        super().__init__("decision_node")

        self.x = -4.0
        self.y = 0.0
        self.theta = 0.0

        self.sensor_data: Dict[str, str] = {}
        self.risk_data: Dict[str, str] = {}

        self.mission_state = "EXPLORANDO"
        self.current_wp_index = 0

        self.alert_sent_person = False
        self.alert_sent_complete = False
        self.alert_count = 0
        self.high_risk_count = 0
        self.extreme_risk_count = 0

        # Ruta extendida.
        # Incluye puntos de rodeo para evitar que el robot se quede trabado en escombros/riesgo alto.
        self.waypoints = [
            {"name": "Entrada del edificio", "x": -3.0, "y": 0.0},
            {"name": "Pasillo principal", "x": -1.2, "y": 0.2},
            {"name": "Zona de escombros inicial", "x": 1.3, "y": 0.8},
            {"name": "Desvío seguro superior", "x": 2.4, "y": 0.3},
            {"name": "Corredor alternativo", "x": 3.5, "y": 1.2},
            {"name": "Borde de zona crítica", "x": 4.7, "y": 2.0},
            {"name": "Rodeo de zona de riesgo alto", "x": 5.7, "y": 2.2},
            {"name": "Zona probable de víctima", "x": 6.8, "y": 2.6},
        ]

        self.create_subscription(Odometry, "/robot/pose", self.pose_callback, 10)
        self.create_subscription(String, "/robot/sensor_status", self.sensor_callback, 10)
        self.create_subscription(String, "/robot/risk_status", self.risk_callback, 10)

        self.cmd_pub = self.create_publisher(Twist, "/robot/cmd_vel", 10)
        self.alert_pub = self.create_publisher(String, "/base/alertas", 10)
        self.state_pub = self.create_publisher(String, "/mission/state", 10)
        self.objective_pub = self.create_publisher(String, "/mission/current_objective", 10)
        self.decision_pub = self.create_publisher(String, "/mission/decision_status", 10)

        self.timer = self.create_timer(1.0, self.decision_loop)

        self.get_logger().info("Decision Node iniciado. Exploración autónoma extendida activa.")

    # =========================================================
    # Callbacks
    # =========================================================

    def pose_callback(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w

        # Yaw 2D desde quaternion simplificado.
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
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def current_objective(self) -> Dict[str, float]:
        return self.waypoints[min(self.current_wp_index, len(self.waypoints) - 1)]

    def advance_waypoint_if_needed(self):
        wp = self.current_objective()

        if self.distance_to(wp) < 0.55 and self.current_wp_index < len(self.waypoints) - 1:
            self.current_wp_index += 1
            wp_next = self.current_objective()
            self.send_alert(f"Waypoint alcanzado. Nuevo objetivo: {wp_next['name']}")

    def compute_navigation_command(self, max_speed: float):
        wp = self.current_objective()

        dx = wp["x"] - self.x
        dy = wp["y"] - self.y

        distance = math.sqrt(dx * dx + dy * dy)

        desired_theta = math.atan2(dy, dx)
        angle_error = self.normalize_angle(desired_theta - self.theta)

        angular = max(-1.1, min(1.1, 1.8 * angle_error))

        # Avanza más lento cerca del objetivo.
        linear = min(max_speed, max(0.08, 0.45 * distance))

        # Si está muy desalineado, gira casi en el lugar.
        if abs(angle_error) > 1.15:
            linear = 0.05

        return linear, angular

    def compute_risk_avoidance_command(self):
        """
        Maniobra evasiva simple.
        En vez de quedarse girando o abortar, el robot avanza lento con giro
        para rodear la zona crítica y luego retoma el waypoint.
        """

        wp = self.current_objective()

        # Si el objetivo está por arriba, rodea hacia abajo.
        # Si el objetivo está por abajo, rodea hacia arriba.
        if wp["y"] >= self.y:
            angular = -0.65
        else:
            angular = 0.65

        linear = 0.16

        return linear, angular

    # =========================================================
    # Decisión principal
    # =========================================================

    def decision_loop(self):
        self.advance_waypoint_if_needed()

        wp = self.current_objective()

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

        risk_extreme = gas > 340 or vib > 2.4 or inc > 34 or temp > 52
        risk_high = nivel == "Alto" or gas > 245 or vib > 1.55 or inc > 23
        risk_medium = nivel == "Medio" or gas > 150 or vib > 0.9 or inc > 14

        # 1. Víctima detectada
        if persona == 1:
            self.mission_state = "VICTIMA_DETECTADA"
            self.send_cmd(0.0, 0.0)

            decision = "Víctima probable detectada. Detenerse, señalizar ubicación y enviar alerta."

            if not self.alert_sent_person:
                self.send_alert(
                    "Posible víctima detectada. "
                    "Robot detenido en zona final. Se requiere intervención del equipo de rescate."
                )
                self.alert_sent_person = True

        # 2. Batería crítica
        elif bateria < 12:
            self.mission_state = "RETORNANDO_BASE"
            self.current_wp_index = 0

            linear, angular = self.compute_navigation_command(max_speed=0.25)
            self.send_cmd(linear, angular)

            decision = "Batería crítica. Retornar hacia entrada/base."
            self.send_alert("Batería crítica. Robot inicia retorno a base.")

        # 3. Riesgo extremo sostenido
        elif risk_extreme:
            self.extreme_risk_count += 1
            self.mission_state = "EVITANDO_RIESGO_EXTREMO"

            linear, angular = self.compute_risk_avoidance_command()
            self.send_cmd(linear, angular)

            decision = (
                "Riesgo extremo detectado. Ejecutar maniobra evasiva, "
                "mantener exploración si la condición no se sostiene."
            )

            self.send_alert(
                f"Riesgo extremo. gas={gas:.1f}, vib={vib:.2f}, "
                f"inc={inc:.1f}, temp={temp:.1f}"
            )

            if self.extreme_risk_count >= 8:
                self.mission_state = "MISION_ABORTADA"
                self.send_cmd(0.0, 0.0)
                decision = "Riesgo extremo sostenido. Misión abortada por seguridad."
                self.send_alert("Misión abortada por riesgo extremo sostenido.")

        # 4. Riesgo alto evitable
        elif risk_high:
            self.high_risk_count += 1
            self.extreme_risk_count = 0
            self.mission_state = "RODEANDO_ZONA_CRITICA"

            linear, angular = self.compute_risk_avoidance_command()
            self.send_cmd(linear, angular)

            decision = (
                "Riesgo alto. No se aborta la misión: "
                "se rodea la zona crítica y luego se continúa hacia la víctima probable."
            )

            if self.high_risk_count in [1, 4, 8]:
                self.send_alert(
                    f"Riesgo alto evitable. nivel={nivel}, gas={gas:.1f}, "
                    f"vib={vib:.2f}, inc={inc:.1f}, temp={temp:.1f}"
                )

        # 5. Obstáculo cercano
        elif obstaculo < 0.65:
            self.extreme_risk_count = 0
            self.mission_state = "EVITANDO_OBSTACULO"

            angular = -0.75 if self.y > wp["y"] else 0.75
            self.send_cmd(0.12, angular)

            decision = "Obstáculo cercano. Maniobra evasiva corta y continuidad de exploración."

        # 6. Riesgo medio
        elif risk_medium:
            self.extreme_risk_count = 0
            self.mission_state = "EXPLORANDO_CON_PRECAUCION"

            linear, angular = self.compute_navigation_command(max_speed=0.32)
            self.send_cmd(linear, angular)

            decision = "Riesgo medio. Avanzar con precaución hacia el siguiente objetivo."

        # 7. Riesgo bajo
        else:
            self.high_risk_count = max(0, self.high_risk_count - 1)
            self.extreme_risk_count = 0
            self.mission_state = "EXPLORANDO"

            linear, angular = self.compute_navigation_command(max_speed=0.62)
            self.send_cmd(linear, angular)

            decision = "Riesgo bajo. Continuar exploración hacia waypoint."

        # Fin de ruta si llega a la zona probable y no detectó persona.
        if (
            self.current_wp_index == len(self.waypoints) - 1
            and self.distance_to(self.current_objective()) < 0.65
            and self.mission_state not in ["VICTIMA_DETECTADA", "MISION_ABORTADA"]
        ):
            self.mission_state = "ZONA_VICTIMA_INSPECCIONADA"
            self.send_cmd(0.0, 0.0)
            decision = "Zona probable de víctima alcanzada e inspeccionada."

            if not self.alert_sent_complete:
                self.send_alert("Zona probable de víctima alcanzada e inspeccionada.")
                self.alert_sent_complete = True

        objective_text = (
            f"{wp['name']} | target=({wp['x']:.2f}, {wp['y']:.2f}) | "
            f"robot=({self.x:.2f}, {self.y:.2f}) | "
            f"waypoint={self.current_wp_index + 1}/{len(self.waypoints)}"
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