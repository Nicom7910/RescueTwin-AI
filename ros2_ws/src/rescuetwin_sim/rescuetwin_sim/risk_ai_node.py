import os
import joblib
import pandas as pd

import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32, Int32, String


class RiskAINode(Node):
    def __init__(self):
        super().__init__("risk_ai_node")

        # ==========================
        # Estado inicial de sensores
        # ==========================

        self.temperatura = 25.0
        self.gas_ppm = 0.0
        self.vibracion = 0.2
        self.inclinacion = 5.0
        self.bateria = 100.0
        self.distancia_obstaculo = 5.0
        self.persona_detectada = 0

        # Variables adicionales necesarias para el modelo
        self.humedad = 55.0
        self.presion = 1013.0
        self.luz = 40.0
        self.sonido_db = 50.0
        self.co2 = 900.0
        self.particulas_pm25 = 40.0
        self.gas_tipo = "sin_gas"
        self.velocidad_robot = 0.5
        self.senal_comunicacion = 80.0
        self.voltaje_bateria = 12.0
        self.temperatura_bateria = 30.0
        self.autonomia_estimada_min = 45.0
        self.visibilidad = 70.0
        self.confianza_persona = 0.2

        # ==========================
        # Cargar modelo IA
        # ==========================

        self.modelo, self.columnas_modelo = self.cargar_modelo()

        # ==========================
        # Suscripciones a sensores
        # ==========================

        self.create_subscription(Float32, "/robot/temperatura", self.temp_callback, 10)
        self.create_subscription(Float32, "/robot/gas_ppm", self.gas_callback, 10)
        self.create_subscription(Float32, "/robot/vibracion", self.vib_callback, 10)
        self.create_subscription(Float32, "/robot/inclinacion", self.inc_callback, 10)
        self.create_subscription(Float32, "/robot/bateria", self.bat_callback, 10)
        self.create_subscription(Float32, "/robot/distancia_obstaculo", self.obs_callback, 10)
        self.create_subscription(Int32, "/robot/persona_detectada", self.person_callback, 10)

        # ==========================
        # Publishers de salida IA
        # ==========================

        self.risk_pub = self.create_publisher(String, "/robot/nivel_riesgo", 10)
        self.action_pub = self.create_publisher(String, "/robot/accion_recomendada", 10)
        self.status_pub = self.create_publisher(String, "/robot/risk_status", 10)

        self.timer = self.create_timer(1.0, self.predict_risk)

        self.get_logger().info("Risk AI Node iniciado. Modelo IA cargado correctamente.")

    # ==========================
    # Carga del modelo
    # ==========================

    def cargar_modelo(self):
        posibles_rutas = [
            "/workspace/RescueTwin-AI/models",
            os.path.abspath(os.path.join(os.getcwd(), "..", "models")),
            os.path.abspath(os.path.join(os.getcwd(), "..", "..", "models")),
        ]

        model_path = None
        columns_path = None

        for ruta in posibles_rutas:
            posible_modelo = os.path.join(ruta, "random_forest_rescuetwin.pkl")
            posibles_columnas = os.path.join(ruta, "model_columns.pkl")

            if os.path.exists(posible_modelo) and os.path.exists(posibles_columnas):
                model_path = posible_modelo
                columns_path = posibles_columnas
                break

        if model_path is None or columns_path is None:
            raise FileNotFoundError(
                "No se encontraron los archivos del modelo. Verificar que existan:\n"
                "models/random_forest_rescuetwin.pkl\n"
                "models/model_columns.pkl"
            )

        modelo = joblib.load(model_path)
        columnas = joblib.load(columns_path)

        self.get_logger().info(f"Modelo cargado desde: {model_path}")

        return modelo, columnas

    # ==========================
    # Callbacks de sensores
    # ==========================

    def temp_callback(self, msg):
        self.temperatura = msg.data

    def gas_callback(self, msg):
        self.gas_ppm = msg.data

        if self.gas_ppm < 50:
            self.gas_tipo = "sin_gas"
        elif self.gas_ppm < 150:
            self.gas_tipo = "humo"
        elif self.gas_ppm < 300:
            self.gas_tipo = "monoxido_carbono"
        else:
            self.gas_tipo = "gas_desconocido"

    def vib_callback(self, msg):
        self.vibracion = msg.data

    def inc_callback(self, msg):
        self.inclinacion = msg.data

    def bat_callback(self, msg):
        self.bateria = msg.data
        self.voltaje_bateria = 10.5 + (self.bateria / 100) * 2.1
        self.autonomia_estimada_min = max(0.0, self.bateria * 0.8 - self.temperatura_bateria * 0.15)

    def obs_callback(self, msg):
        self.distancia_obstaculo = msg.data

    def person_callback(self, msg):
        self.persona_detectada = msg.data
        self.confianza_persona = 0.9 if self.persona_detectada == 1 else 0.2

    # ==========================
    # Preparar entrada del modelo
    # ==========================

    def preparar_entrada_modelo(self):
        datos = {
            "temperatura": self.temperatura,
            "humedad": self.humedad,
            "presion": self.presion,
            "luz": self.luz,
            "sonido_db": self.sonido_db,
            "co2": self.co2,
            "particulas_pm25": self.particulas_pm25,
            "gas_tipo": self.gas_tipo,
            "gas_ppm": self.gas_ppm,
            "vibracion": self.vibracion,
            "inclinacion": self.inclinacion,
            "distancia_obstaculo": self.distancia_obstaculo,
            "velocidad_robot": self.velocidad_robot,
            "senal_comunicacion": self.senal_comunicacion,
            "bateria": self.bateria,
            "voltaje_bateria": self.voltaje_bateria,
            "temperatura_bateria": self.temperatura_bateria,
            "autonomia_estimada_min": self.autonomia_estimada_min,
            "visibilidad": self.visibilidad,
            "persona_detectada": self.persona_detectada,
            "confianza_persona": self.confianza_persona,
        }

        df_input = pd.DataFrame([datos])

        df_input = pd.get_dummies(df_input, columns=["gas_tipo"], drop_first=True)

        for col in self.columnas_modelo:
            if col not in df_input.columns:
                df_input[col] = 0

        df_input = df_input[self.columnas_modelo]

        return df_input

    # ==========================
    # Recomendación de acción
    # ==========================

    def recomendar_accion(self, nivel_riesgo):
        if self.bateria < 20:
            return "Volver a base por bateria baja"

        if nivel_riesgo == "Bajo" and self.persona_detectada == 0:
            return "Avanzar"

        if nivel_riesgo == "Bajo" and self.persona_detectada == 1:
            return "Enviar alerta y continuar exploracion"

        if nivel_riesgo == "Medio" and self.persona_detectada == 0:
            return "Avanzar con precaucion"

        if nivel_riesgo == "Medio" and self.persona_detectada == 1:
            return "Enviar alerta y avanzar con precaucion"

        if nivel_riesgo == "Alto" and self.persona_detectada == 0:
            return "Cambiar ruta o detenerse"

        if nivel_riesgo == "Alto" and self.persona_detectada == 1:
            return "Enviar alerta y cambiar ruta"

        return "Revisar manualmente"

    # ==========================
    # Predicción IA
    # ==========================

    def predict_risk(self):
        entrada = self.preparar_entrada_modelo()

        nivel_riesgo = self.modelo.predict(entrada)[0]
        accion = self.recomendar_accion(nivel_riesgo)

        msg_risk = String()
        msg_risk.data = str(nivel_riesgo)
        self.risk_pub.publish(msg_risk)

        msg_action = String()
        msg_action.data = accion
        self.action_pub.publish(msg_action)

        msg_status = String()
        msg_status.data = (
            f"Riesgo IA | "
            f"nivel={nivel_riesgo} | "
            f"accion={accion} | "
            f"temp={self.temperatura:.1f}C | "
            f"gas={self.gas_ppm:.1f}ppm | "
            f"vib={self.vibracion:.2f} | "
            f"inc={self.inclinacion:.1f}deg | "
            f"bateria={self.bateria:.1f}% | "
            f"obstaculo={self.distancia_obstaculo:.2f}m | "
            f"persona={self.persona_detectada}"
        )
        self.status_pub.publish(msg_status)


def main(args=None):
    rclpy.init(args=args)
    node = RiskAINode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()