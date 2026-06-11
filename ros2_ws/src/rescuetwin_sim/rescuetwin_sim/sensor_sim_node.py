import math
import random

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry
from std_msgs.msg import String


class SensorSimNode(Node):
    """
    Simulador de sensores para RescueTwin AI.

    Mejora:
    - Los sensores ya no son totalmente aleatorios.
    - Ahora dependen de la posición del robot en el mapa.
    - La víctima probable se detecta al acercarse a la zona final.
    - Las zonas de riesgo alto generan gas/vibración/inclinación más altos.
    """

    def __init__(self):
        super().__init__("sensor_sim_node")

        self.x = -4.0
        self.y = 0.0
        self.battery = 100.0

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

        self.timer = self.create_timer(1.0, self.publish_sensor_data)

        self.zones = {
            "entrada": (-3.0, 0.0),
            "escombros": (1.5, 0.8),
            "riesgo_medio": (3.0, -2.8),
            "riesgo_alto": (5.0, 2.8),
            "victima_probable": (6.8, 2.6),
        }

        self.get_logger().info("Sensor Sim Node iniciado con sensores dependientes de posición.")

    def pose_callback(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

    def distance_to(self, point) -> float:
        px, py = point
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)

    def clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(value, max_value))

    def publish_sensor_data(self):
        d_escombros = self.distance_to(self.zones["escombros"])
        d_riesgo_medio = self.distance_to(self.zones["riesgo_medio"])
        d_riesgo_alto = self.distance_to(self.zones["riesgo_alto"])
        d_victima = self.distance_to(self.zones["victima_probable"])

        # Base normal
        temperature = 24.0 + random.uniform(-1.5, 1.5)
        gas_ppm = 60.0 + random.uniform(-12.0, 12.0)
        vibration = 0.25 + random.uniform(-0.08, 0.08)
        inclination = 4.0 + random.uniform(-1.5, 1.5)
        obstacle_distance = 3.0 + random.uniform(-0.6, 0.6)
        person_detected = 0

        # Zona de escombros
        if d_escombros < 1.4:
            obstacle_distance = 0.6 + random.uniform(0.0, 0.6)
            vibration += 0.35
            inclination += 5.0

        # Zona de riesgo medio
        if d_riesgo_medio < 1.5:
            gas_ppm += 80.0
            temperature += 3.0
            vibration += 0.35

        # Zona de riesgo alto.
        # Se simula riesgo, pero no de forma permanente para que el robot pueda rodear y continuar.
        if d_riesgo_alto < 1.7:
            gas_ppm += 150.0
            temperature += 5.0
            vibration += 0.75
            inclination += 9.0
            obstacle_distance = min(obstacle_distance, 1.1 + random.uniform(0.0, 0.7))

        # Víctima probable
        if d_victima < 0.9:
            person_detected = 1
            obstacle_distance = max(obstacle_distance, 1.4)

        # Batería decrece lentamente
        self.battery -= random.uniform(0.08, 0.22)
        self.battery = self.clamp(self.battery, 5.0, 100.0)

        temperature = self.clamp(temperature, 10.0, 60.0)
        gas_ppm = self.clamp(gas_ppm, 20.0, 420.0)
        vibration = self.clamp(vibration, 0.0, 3.0)
        inclination = self.clamp(inclination, 0.0, 40.0)
        obstacle_distance = self.clamp(obstacle_distance, 0.3, 5.0)

        msg = String()
        msg.data = (
            f"Sensores | "
            f"x={self.x:.2f}, y={self.y:.2f}, "
            f"temp={temperature:.1f}C, "
            f"gas={gas_ppm:.1f}ppm, "
            f"vib={vibration:.2f}, "
            f"inc={inclination:.1f}, "
            f"bateria={self.battery:.1f}, "
            f"obstaculo={obstacle_distance:.2f}, "
            f"persona={person_detected}"
        )

        self.sensor_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SensorSimNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()