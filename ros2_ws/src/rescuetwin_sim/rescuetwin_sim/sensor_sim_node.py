import math
import random

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry
from std_msgs.msg import Float32, Int32, String


class SensorSimNode(Node):
    def __init__(self):
        super().__init__("sensor_sim_node")

        # Posición actual del robot
        self.x = -4.0
        self.y = 0.0

        # Estado operativo
        self.bateria = 100.0

        # Zonas simuladas del mundo
        self.risk_high_zone = (5.0, 2.8)
        self.risk_medium_zone = (3.0, -2.8)
        self.victim_zone = (7.0, 2.6)

        # Suscripción a la pose del robot
        self.pose_sub = self.create_subscription(
            Odometry,
            "/robot/pose",
            self.pose_callback,
            10
        )

        # Publishers de sensores
        self.temp_pub = self.create_publisher(Float32, "/robot/temperatura", 10)
        self.gas_pub = self.create_publisher(Float32, "/robot/gas_ppm", 10)
        self.vib_pub = self.create_publisher(Float32, "/robot/vibracion", 10)
        self.inc_pub = self.create_publisher(Float32, "/robot/inclinacion", 10)
        self.bat_pub = self.create_publisher(Float32, "/robot/bateria", 10)
        self.obs_pub = self.create_publisher(Float32, "/robot/distancia_obstaculo", 10)
        self.person_pub = self.create_publisher(Int32, "/robot/persona_detectada", 10)

        # Publisher resumen
        self.status_pub = self.create_publisher(String, "/robot/sensor_status", 10)

        self.timer = self.create_timer(1.0, self.publish_sensors)

        self.get_logger().info("Sensor Sim Node iniciado. Publicando sensores simulados del robot.")

    def pose_callback(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

    def distance_to(self, point):
        px, py = point
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)

    def publish_float(self, publisher, value):
        msg = Float32()
        msg.data = float(value)
        publisher.publish(msg)

    def publish_int(self, publisher, value):
        msg = Int32()
        msg.data = int(value)
        publisher.publish(msg)

    def publish_sensors(self):
        dist_high = self.distance_to(self.risk_high_zone)
        dist_medium = self.distance_to(self.risk_medium_zone)
        dist_victim = self.distance_to(self.victim_zone)

        # ==========================
        # Simulación de sensores
        # ==========================

        # Temperatura sube cerca de la zona de riesgo alto
        temperatura = 24.0 + max(0, 12.0 - dist_high * 2.0) + random.uniform(-1.5, 1.5)

        # Gas aumenta cerca de zonas de riesgo
        gas_ppm = 25.0
        gas_ppm += max(0, 320.0 - dist_high * 55.0)
        gas_ppm += max(0, 130.0 - dist_medium * 35.0)
        gas_ppm += random.uniform(-10.0, 10.0)
        gas_ppm = max(0.0, gas_ppm)

        # Vibración aumenta cerca de zona de alto riesgo
        vibracion = 0.2 + max(0, 2.0 - dist_high * 0.35) + random.uniform(-0.08, 0.08)
        vibracion = max(0.0, min(vibracion, 2.5))

        # Inclinación varía según posición y cercanía a escombros
        inclinacion = 4.0 + max(0, 28.0 - dist_high * 4.5) + random.uniform(-2.0, 2.0)
        inclinacion = max(0.0, min(inclinacion, 35.0))

        # Distancia a obstáculos: menor cerca de zonas de escombros/riesgo
        distancia_obstaculo = 4.5
        distancia_obstaculo -= max(0, 3.8 - dist_high * 0.7)
        distancia_obstaculo -= max(0, 2.0 - dist_medium * 0.4)
        distancia_obstaculo += random.uniform(-0.2, 0.2)
        distancia_obstaculo = max(0.2, min(distancia_obstaculo, 5.0))

        # Persona detectada si está cerca de la víctima simulada
        persona_detectada = 1 if dist_victim < 1.8 else 0

        # Batería baja lentamente
        self.bateria -= 0.15
        self.bateria = max(0.0, self.bateria)

        # ==========================
        # Publicación de topics
        # ==========================

        self.publish_float(self.temp_pub, temperatura)
        self.publish_float(self.gas_pub, gas_ppm)
        self.publish_float(self.vib_pub, vibracion)
        self.publish_float(self.inc_pub, inclinacion)
        self.publish_float(self.bat_pub, self.bateria)
        self.publish_float(self.obs_pub, distancia_obstaculo)
        self.publish_int(self.person_pub, persona_detectada)

        status = String()
        status.data = (
            f"Sensores | "
            f"x={self.x:.2f}, y={self.y:.2f}, "
            f"temp={temperatura:.1f}C, "
            f"gas={gas_ppm:.1f}ppm, "
            f"vib={vibracion:.2f}, "
            f"inc={inclinacion:.1f}deg, "
            f"bateria={self.bateria:.1f}%, "
            f"obstaculo={distancia_obstaculo:.2f}m, "
            f"persona={persona_detectada}"
        )

        self.status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = SensorSimNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()