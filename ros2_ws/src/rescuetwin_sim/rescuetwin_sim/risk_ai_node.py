import os
import re
from pathlib import Path
from typing import Dict, Optional

import joblib
import pandas as pd
import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32, Int32, String


class RiskAINode(Node):
    """
    Nodo de IA para estimación de riesgo.

    Corrección principal:
    - Antes quedaba usando valores por defecto porque escuchaba tópicos Float32
      que no necesariamente estaban siendo publicados.
    - Ahora también escucha /robot/sensor_status, que es el mensaje real generado
      por sensor_sim_node.py.
    - Publica /robot/risk_status con los valores reales recibidos.
    """

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

        self.riesgo_local = "bajo"
        self.tipo_obstaculo = "ninguno"
        self.victim_signal = 0.0
        self.victim_bearing = 0.0
        self.victim_distance = 999.0

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
        # Suscripciones
        # ==========================

        # Suscripción principal actual.
        self.create_subscription(String, "/robot/sensor_status", self.sensor_status_callback, 10)

        # Suscripciones antiguas, se mantienen por compatibilidad.
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

    # =========================================================
    # Carga del modelo
    # =========================================================

    def cargar_modelo(self):
        current = Path.cwd().resolve()

        posibles_rutas = [
            Path("/workspace/RescueTwin-AI/models"),
            current / "models",
            current.parent / "models",
            current.parent.parent / "models",
        ]

        model_path = None
        columns_path = None

        for ruta in posibles_rutas:
            posible_modelo = ruta / "random_forest_rescuetwin.pkl"
            posibles_columnas = ruta / "model_columns.pkl"

            if posible_modelo.exists() and posibles_columnas.exists():
                model_path = posible_modelo
                columns_path = posibles_columnas
                break

        if model_path is None or columns_path is None:
            raise FileNotFoundError(
                "No se encontraron los archivos del modelo.\n"
                "Verificar que existan:\n"
                "models/random_forest_rescuetwin.pkl\n"
                "models/model_columns.pkl"
            )

        modelo = joblib.load(model_path)
        columnas = joblib.load(columns_path)

        self.get_logger().info(f"Modelo cargado desde: {model_path}")

        return modelo, columnas

    # =========================================================
    # Parsing
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

    # =========================================================
    # Actualización de variables
    # =========================================================

    def actualizar_variables_derivadas(self):
        if self.gas_ppm < 50:
            self.gas_tipo = "sin_gas"
        elif self.gas_ppm < 150:
            self.gas_tipo = "humo"
        elif self.gas_ppm < 300:
            self.gas_tipo = "monoxido_carbono"
        else:
            self.gas_tipo = "gas_desconocido"

        self.voltaje_bateria = 10.5 + (self.bateria / 100.0) * 2.1
        self.autonomia_estimada_min = max(
            0.0,
            self.bateria * 0.8 - self.temperatura_bateria * 0.15,
        )

        self.confianza_persona = 0.9 if self.persona_detectada == 1 else max(
            0.2,
            min(0.85, self.victim_signal),
        )

        self.visibilidad = max(
            10.0,
            min(100.0, 90.0 - self.gas_ppm * 0.10 - self.particulas_pm25 * 0.15),
        )

        self.co2 = 850.0 + self.gas_ppm * 1.8
        self.particulas_pm25 = max(20.0, min(180.0, 35.0 + self.gas_ppm * 0.20))

    # =========================================================
    # Callbacks principales
    # =========================================================

    def sensor_status_callback(self, msg: String):
        data = self.parse_status(msg.data)

        self.temperatura = self.to_float(data.get("temp"), self.temperatura)
        self.gas_ppm = self.to_float(data.get("gas"), self.gas_ppm)
        self.vibracion = self.to_float(data.get("vib"), self.vibracion)
        self.inclinacion = self.to_float(data.get("inc"), self.inclinacion)
        self.bateria = self.to_float(data.get("bateria"), self.bateria)
        self.distancia_obstaculo = self.to_float(data.get("obstaculo"), self.distancia_obstaculo)
        self.persona_detectada = int(self.to_float(data.get("persona"), self.persona_detectada))

        self.riesgo_local = data.get("riesgo_local", self.riesgo_local)
        self.tipo_obstaculo = data.get("tipo_obstaculo", self.tipo_obstaculo)

        self.victim_signal = self.to_float(data.get("victim_signal"), self.victim_signal)
        self.victim_bearing = self.to_float(data.get("victim_bearing"), self.victim_bearing)
        self.victim_distance = self.to_float(data.get("victim_distance"), self.victim_distance)

        self.actualizar_variables_derivadas()

    # =========================================================
    # Callbacks de compatibilidad
    # =========================================================

    def temp_callback(self, msg):
        self.temperatura = float(msg.data)
        self.actualizar_variables_derivadas()

    def gas_callback(self, msg):
        self.gas_ppm = float(msg.data)
        self.actualizar_variables_derivadas()

    def vib_callback(self, msg):
        self.vibracion = float(msg.data)
        self.actualizar_variables_derivadas()

    def inc_callback(self, msg):
        self.inclinacion = float(msg.data)
        self.actualizar_variables_derivadas()

    def bat_callback(self, msg):
        self.bateria = float(msg.data)
        self.actualizar_variables_derivadas()

    def obs_callback(self, msg):
        self.distancia_obstaculo = float(msg.data)
        self.actualizar_variables_derivadas()

    def person_callback(self, msg):
        self.persona_detectada = int(msg.data)
        self.actualizar_variables_derivadas()

    # =========================================================
    # Modelo
    # =========================================================

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

    def heuristic_risk_level(self):
        if (
            self.riesgo_local == "alto"
            or self.gas_ppm > 270
            or self.vibracion > 1.8
            or self.inclinacion > 27
            or self.temperatura > 55
            or self.distancia_obstaculo < 0.30
        ):
            return "Alto"

        if (
            self.riesgo_local == "medio"
            or self.gas_ppm > 150
            or self.vibracion > 1.0
            or self.inclinacion > 16
            or self.temperatura > 42
            or self.distancia_obstaculo < 0.75
        ):
            return "Medio"

        return "Bajo"

    def max_risk_level(self, model_level: str, heuristic_level: str):
        rank = {
            "Bajo": 1,
            "Medio": 2,
            "Alto": 3,
        }

        model_level = str(model_level)

        if model_level not in rank:
            model_level = "Bajo"

        if heuristic_level not in rank:
            heuristic_level = "Bajo"

        return model_level if rank[model_level] >= rank[heuristic_level] else heuristic_level

    def recomendar_accion(self, nivel_riesgo):
        if self.persona_detectada == 1:
            return "Detener robot, enviar alerta y señalizar ubicación de víctima"

        if self.bateria < 20:
            return "Volver a base por bateria baja"

        if self.victim_signal > 0.18 and nivel_riesgo != "Alto":
            return "Priorizar aproximacion controlada hacia señal de víctima"

        if nivel_riesgo == "Bajo":
            return "Avanzar"

        if nivel_riesgo == "Medio":
            return "Avanzar con precaucion"

        if nivel_riesgo == "Alto":
            return "Cambiar ruta, rodear zona o detenerse si el riesgo persiste"

        return "Revisar manualmente"

    # =========================================================
    # Predicción IA
    # =========================================================

    def predict_risk(self):
        entrada = self.preparar_entrada_modelo()

        try:
            nivel_modelo = str(self.modelo.predict(entrada)[0])
        except Exception as exc:
            self.get_logger().error(f"Error al predecir riesgo con el modelo: {exc}")
            nivel_modelo = "Bajo"

        nivel_heuristico = self.heuristic_risk_level()
        nivel_riesgo = self.max_risk_level(nivel_modelo, nivel_heuristico)

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
            f"modelo={nivel_modelo} | "
            f"heuristico={nivel_heuristico} | "
            f"accion={accion} | "
            f"temp={self.temperatura:.1f}C | "
            f"gas={self.gas_ppm:.1f}ppm | "
            f"vib={self.vibracion:.2f} | "
            f"inc={self.inclinacion:.1f}deg | "
            f"bateria={self.bateria:.1f}% | "
            f"obstaculo={self.distancia_obstaculo:.2f}m | "
            f"persona={self.persona_detectada} | "
            f"riesgo_local={self.riesgo_local} | "
            f"victim_signal={self.victim_signal:.2f} | "
            f"victim_distance={self.victim_distance:.2f}"
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