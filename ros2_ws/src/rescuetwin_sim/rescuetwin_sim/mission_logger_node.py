import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry
from std_msgs.msg import String


class MissionLoggerNode(Node):
    """
    Nodo de bitácora de misión.

    Registra periódicamente:
    - pose
    - sensores
    - riesgo IA
    - estado de misión
    - objetivo actual
    - decisión
    - alertas de base

    Archivos generados:
    - reports/mission_logs/ros_mission_<timestamp>.csv
    - reports/mission_logs/ros_mission_<timestamp>.jsonl
    """

    def __init__(self):
        super().__init__("mission_logger_node")

        self.project_dir = Path(os.environ.get("RESCUETWIN_PROJECT_DIR", "/workspace/RescueTwin-AI"))
        self.log_dir = self.project_dir / "reports" / "mission_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = self.log_dir / f"ros_mission_{timestamp}.csv"
        self.jsonl_path = self.log_dir / f"ros_mission_{timestamp}.jsonl"

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

        self.sensor_data: Dict[str, str] = {}
        self.risk_data: Dict[str, str] = {}
        self.mission_state = "SIN_ESTADO"
        self.current_objective = "SIN_OBJETIVO"
        self.decision_status = "SIN_DECISION"
        self.last_alert = "SIN_ALERTAS"

        self.create_subscription(Odometry, "/robot/pose", self.pose_callback, 10)
        self.create_subscription(String, "/robot/sensor_status", self.sensor_callback, 10)
        self.create_subscription(String, "/robot/risk_status", self.risk_callback, 10)
        self.create_subscription(String, "/mission/state", self.state_callback, 10)
        self.create_subscription(String, "/mission/current_objective", self.objective_callback, 10)
        self.create_subscription(String, "/mission/decision_status", self.decision_callback, 10)
        self.create_subscription(String, "/base/alertas", self.alert_callback, 10)

        self.log_status_pub = self.create_publisher(String, "/mission/log_status", 10)

        self.create_csv_header()

        self.timer = self.create_timer(1.0, self.write_log)

        self.get_logger().info(f"Mission Logger iniciado. CSV: {self.csv_path}")
        self.get_logger().info(f"Mission Logger iniciado. JSONL: {self.jsonl_path}")

    def pose_callback(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.z = msg.pose.pose.position.z

    def sensor_callback(self, msg: String):
        self.sensor_data = self.parse_status(msg.data)

    def risk_callback(self, msg: String):
        self.risk_data = self.parse_status(msg.data)

    def state_callback(self, msg: String):
        self.mission_state = msg.data

    def objective_callback(self, msg: String):
        self.current_objective = msg.data

    def decision_callback(self, msg: String):
        self.decision_status = msg.data

    def alert_callback(self, msg: String):
        self.last_alert = msg.data

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

    def create_csv_header(self):
        with self.csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "x",
                "y",
                "z",
                "mission_state",
                "risk_level",
                "recommended_action",
                "temperature",
                "gas_ppm",
                "vibration",
                "inclination",
                "battery",
                "obstacle_distance",
                "person_detected",
                "current_objective",
                "decision_status",
                "last_alert",
            ])

    def build_record(self) -> Dict:
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "z": round(self.z, 4),
            "mission_state": self.mission_state,
            "risk_level": self.risk_data.get("nivel", "Desconocido"),
            "recommended_action": self.risk_data.get("accion", ""),
            "temperature": self.to_float(self.sensor_data.get("temp"), 0.0),
            "gas_ppm": self.to_float(self.sensor_data.get("gas"), 0.0),
            "vibration": self.to_float(self.sensor_data.get("vib"), 0.0),
            "inclination": self.to_float(self.sensor_data.get("inc"), 0.0),
            "battery": self.to_float(self.sensor_data.get("bateria"), 0.0),
            "obstacle_distance": self.to_float(self.sensor_data.get("obstaculo"), 0.0),
            "person_detected": int(self.to_float(self.sensor_data.get("persona"), 0.0)),
            "current_objective": self.current_objective,
            "decision_status": self.decision_status,
            "last_alert": self.last_alert,
        }

    def write_log(self):
        record = self.build_record()

        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                record["timestamp"],
                record["x"],
                record["y"],
                record["z"],
                record["mission_state"],
                record["risk_level"],
                record["recommended_action"],
                record["temperature"],
                record["gas_ppm"],
                record["vibration"],
                record["inclination"],
                record["battery"],
                record["obstacle_distance"],
                record["person_detected"],
                record["current_objective"],
                record["decision_status"],
                record["last_alert"],
            ])

        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        msg = String()
        msg.data = f"Bitácora actualizada | csv={self.csv_path}"
        self.log_status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = MissionLoggerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
