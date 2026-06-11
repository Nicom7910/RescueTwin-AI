#!/usr/bin/env python3
"""
Misión autónoma ROS/Gazebo - RescueTwin AI

Este script ejecuta una demo más realista del proyecto RescueTwin AI.

A diferencia de `demo_rescuetwin_ros.py`, esta versión simula una misión de rescate:
- Levanta el contenedor Docker.
- Compila el workspace ROS 2.
- Inicia los nodos:
  - motion_node
  - sensor_sim_node
  - risk_ai_node
- Lee sensores y riesgo IA.
- Toma decisiones automáticas.
- Simula eventos aleatorios de emergencia.
- Mueve el robot según el estado de la misión.
- Genera una bitácora final en reports/mission_logs/.

Ejecutar desde la raíz del proyecto:

    python3 demo_rescuetwin_mission.py

Opciones:

    python3 demo_rescuetwin_mission.py --steps 10
    python3 demo_rescuetwin_mission.py --steps 10 --seed 42
    python3 demo_rescuetwin_mission.py --skip-gazebo-check

Requisitos:
- Docker Desktop abierto.
- Imagen Docker: rescuetwin_ros_image.
- Proyecto en: /Users/nicom7910/Downloads/RescueTwin-AI.
- Modelos:
    models/random_forest_rescuetwin.pkl
    models/model_columns.pkl
"""

import argparse
import json
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CONTAINER_NAME = "rescuetwin_ros"
IMAGE_NAME = "rescuetwin_ros_image"

CONTAINER_PROJECT_DIR = "/workspace/RescueTwin-AI"
CONTAINER_WS_DIR = f"{CONTAINER_PROJECT_DIR}/ros2_ws"

MISSION_LOG_DIR = PROJECT_DIR / "reports" / "mission_logs"


# ============================================================
# Utilidades generales
# ============================================================

def print_title(text: str) -> None:
    print("\n" + "=" * 90)
    print(text)
    print("=" * 90)


def print_step(text: str) -> None:
    print(f"\n[+] {text}")


def run_host(command: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)
    return subprocess.run(command, check=check)


def run_host_shell(command: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)
    return subprocess.run(command, shell=True, check=check)


def docker_exec(command: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    full_command = ["docker", "exec", CONTAINER_NAME, "bash", "-lc", command]
    if capture:
        return subprocess.run(full_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)
    return subprocess.run(full_command, check=check)


def ros_command(command: str) -> str:
    return (
        "set +u && "
        "source /opt/ros/humble/setup.bash && "
        f"cd {CONTAINER_WS_DIR} && "
        "source install/setup.bash && "
        f"{command}"
    )


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# Docker / ROS
# ============================================================

def check_docker() -> None:
    print_step("Verificando Docker")
    try:
        result = run_host(["docker", "ps"], capture=True)
        print(result.stdout.strip())
    except Exception:
        print(
            "\nERROR: Docker no está disponible.\n"
            "Abrí Docker Desktop y esperá a que quede corriendo. Después ejecutá nuevamente este script."
        )
        sys.exit(1)


def container_exists() -> bool:
    result = run_host_shell(
        f"docker ps -a --format '{{{{.Names}}}}' | grep -w {CONTAINER_NAME}",
        check=False,
        capture=True,
    )
    return result.returncode == 0


def container_running() -> bool:
    result = run_host_shell(
        f"docker ps --format '{{{{.Names}}}}' | grep -w {CONTAINER_NAME}",
        check=False,
        capture=True,
    )
    return result.returncode == 0


def image_exists() -> bool:
    result = run_host_shell(
        f"docker images --format '{{{{.Repository}}}}' | grep -w {IMAGE_NAME}",
        check=False,
        capture=True,
    )
    return result.returncode == 0


def start_or_create_container() -> None:
    print_step("Levantando contenedor Docker")

    if container_exists():
        if not container_running():
            run_host(["docker", "start", CONTAINER_NAME])
        else:
            print(f"El contenedor {CONTAINER_NAME} ya está corriendo.")
        return

    if not image_exists():
        print(
            f"\nERROR: No existe la imagen Docker {IMAGE_NAME}.\n"
            "Verificá con:\n"
            "    docker images\n"
        )
        sys.exit(1)

    command = [
        "docker",
        "run",
        "-dit",
        "--name",
        CONTAINER_NAME,
        "-e",
        "DISPLAY=host.docker.internal:0",
        "-e",
        "SDL_AUDIODRIVER=dummy",
        "-e",
        "QT_X11_NO_MITSHM=1",
        "-e",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "-v",
        f"{PROJECT_DIR}:{CONTAINER_PROJECT_DIR}",
        IMAGE_NAME,
        "bash",
    ]

    run_host(command)


def check_project_inside_container() -> None:
    print_step("Verificando proyecto dentro del contenedor")

    result = docker_exec(f"cd {CONTAINER_PROJECT_DIR} && ls", capture=True)
    print(result.stdout.strip())

    required_paths = [
        "models/random_forest_rescuetwin.pkl",
        "models/model_columns.pkl",
        "ros2_ws/src/rescuetwin_sim",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/motion_node.py",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/sensor_sim_node.py",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/risk_ai_node.py",
    ]

    for relative_path in required_paths:
        check_cmd = f"test -e {CONTAINER_PROJECT_DIR}/{relative_path}"
        result = docker_exec(check_cmd, check=False, capture=True)
        if result.returncode != 0:
            print(f"\nERROR: Falta el archivo o carpeta: {relative_path}")
            sys.exit(1)


def check_python_versions() -> None:
    print_step("Verificando librerías Python para IA")

    command = (
        "python3 - << 'PY'\n"
        "import numpy, scipy, sklearn, pandas, joblib\n"
        "print('numpy', numpy.__version__)\n"
        "print('scipy', scipy.__version__)\n"
        "print('sklearn', sklearn.__version__)\n"
        "print('pandas', pandas.__version__)\n"
        "print('joblib', joblib.__version__)\n"
        "PY"
    )

    result = docker_exec(command, capture=True, check=False)
    print(result.stdout.strip())

    if result.returncode != 0:
        print("\nERROR: No se pudieron importar las librerías necesarias.")
        sys.exit(1)


def check_model_loads() -> None:
    print_step("Verificando carga del modelo Random Forest")

    command = (
        f"cd {CONTAINER_PROJECT_DIR} && "
        "python3 - << 'PY'\n"
        "import joblib\n"
        "modelo = joblib.load('models/random_forest_rescuetwin.pkl')\n"
        "columnas = joblib.load('models/model_columns.pkl')\n"
        "print('Modelo cargado OK')\n"
        "print(type(modelo))\n"
        "print('Columnas:', len(columnas))\n"
        "PY"
    )

    result = docker_exec(command, capture=True, check=False)
    print(result.stdout.strip())

    if result.returncode != 0:
        print(
            "\nERROR: El modelo no pudo cargarse.\n"
            "Posible incompatibilidad de versiones.\n\n"
            "Dentro del contenedor podés corregir con:\n"
            "pip3 uninstall -y numpy scipy scikit-learn pandas joblib\n"
            "pip3 install --no-cache-dir numpy==2.2.6 scipy==1.15.3 scikit-learn==1.7.2 pandas==2.3.3 joblib==1.5.3\n"
        )
        sys.exit(1)


def build_workspace() -> None:
    print_step("Compilando workspace ROS 2")

    command = (
        "set +u && "
        "source /opt/ros/humble/setup.bash && "
        f"cd {CONTAINER_WS_DIR} && "
        "rm -rf build install log && "
        "colcon build && "
        "source install/setup.bash && "
        "ros2 pkg list | grep rescuetwin_sim"
    )

    result = docker_exec(command, capture=True)
    print(result.stdout.strip())


def validate_gazebo_world_headless() -> None:
    print_step("Validando mundo Gazebo en modo headless")

    command = (
        f"cd {CONTAINER_PROJECT_DIR} && "
        "timeout 5s gzserver ros2_ws/src/rescuetwin_sim/worlds/collapse_world.world --verbose"
    )

    result = docker_exec(command, check=False, capture=True)
    output = result.stdout.strip()
    lines = output.splitlines()

    print("\n".join(lines[:20]))

    if "Loading world file" in output or "Connected to gazebo master" in output:
        print("Mundo Gazebo validado correctamente en modo headless.")
    else:
        print("Advertencia: no se pudo confirmar la carga del mundo Gazebo, pero la misión ROS continuará.")


def stop_previous_nodes() -> None:
    print_step("Deteniendo nodos anteriores si quedaron corriendo")
    docker_exec("pkill -f 'motion_node|sensor_sim_node|risk_ai_node' || true", check=False)


def start_node_detached(node_name: str) -> None:
    print_step(f"Iniciando nodo: {node_name}")

    command = ros_command(f"nohup ros2 run rescuetwin_sim {node_name} > /tmp/{node_name}.log 2>&1 &")
    docker_exec(command)
    time.sleep(1.5)

    log = docker_exec(f"tail -n 20 /tmp/{node_name}.log || true", capture=True, check=False)
    if log.stdout.strip():
        print(log.stdout.strip())


def wait_for_topic(topic: str, timeout_seconds: int = 15) -> bool:
    print_step(f"Esperando topic {topic}")

    start = time.time()
    while time.time() - start < timeout_seconds:
        result = docker_exec(ros_command("ros2 topic list"), capture=True, check=False)
        if topic in result.stdout:
            print(f"Topic disponible: {topic}")
            return True
        time.sleep(1)

    print(f"Advertencia: no apareció el topic {topic}")
    return False


# ============================================================
# ROS IO
# ============================================================

def echo_once(topic: str, timeout_seconds: int = 10) -> str:
    command = ros_command(f"timeout {timeout_seconds}s ros2 topic echo {topic} --once")
    result = docker_exec(command, capture=True, check=False)
    output = result.stdout.strip()
    return output if output else "(sin datos)"


def publish_cmd(linear_x: float, angular_z: float) -> None:
    command = ros_command(
        "ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "
        f"\"{{linear: {{x: {linear_x:.3f}}}, angular: {{z: {angular_z:.3f}}}}}\""
    )
    docker_exec(command, capture=True, check=False)


def stop_robot() -> None:
    publish_cmd(0.0, 0.0)


# ============================================================
# Parsing de mensajes
# ============================================================

def extract_string_data(echo_output: str) -> str:
    """
    Convierte salida tipo:
        data: Riesgo IA | nivel=...
    en:
        Riesgo IA | nivel=...
    """
    for line in echo_output.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return line.replace("data:", "", 1).strip()
    return echo_output.strip()


def parse_key_value_status(text: str) -> dict:
    """
    Parsea textos como:
        Riesgo IA | nivel=Bajo | accion=Avanzar | temp=25.0C | gas=10.0ppm
    o:
        Sensores | x=1.0, y=2.0, temp=...
    """
    clean = extract_string_data(text)
    clean = clean.replace(",", " |")
    parts = [p.strip() for p in clean.split("|")]

    data = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default

    match = re.search(r"-?\d+(\.\d+)?", value)
    if not match:
        return default

    return float(match.group(0))


def get_robot_status() -> dict:
    text = echo_once("/robot/status")
    data = parse_key_value_status(text)
    data["_raw"] = extract_string_data(text)
    return data


def get_sensor_status() -> dict:
    text = echo_once("/robot/sensor_status")
    data = parse_key_value_status(text)
    data["_raw"] = extract_string_data(text)
    return data


def get_risk_status() -> dict:
    text = echo_once("/robot/risk_status")
    data = parse_key_value_status(text)
    data["_raw"] = extract_string_data(text)
    return data


# ============================================================
# Eventos y decisiones
# ============================================================

def generate_random_event(event_probability: float) -> dict | None:
    """
    Genera eventos de misión aleatorios.
    No modifica directamente los nodos ROS, pero sí influye en la decisión
    de movimiento para simular condiciones operativas.
    """
    if random.random() > event_probability:
        return None

    events = [
        {
            "type": "derrumbe_secundario",
            "description": "Derrumbe secundario detectado: se prioriza reducir velocidad y girar.",
            "severity": "alta",
        },
        {
            "type": "obstaculo_inesperado",
            "description": "Obstáculo inesperado en el camino: se ejecuta maniobra evasiva.",
            "severity": "media",
        },
        {
            "type": "humo_denso",
            "description": "Humo denso detectado: se avanza con precaución y monitoreo de gas.",
            "severity": "media",
        },
        {
            "type": "perdida_comunicacion",
            "description": "Pérdida parcial de comunicación: se reduce velocidad.",
            "severity": "media",
        },
        {
            "type": "ruido_de_victima",
            "description": "Posible señal acústica de víctima: se orienta la exploración hacia la zona crítica.",
            "severity": "alta",
        },
    ]

    return random.choice(events)


def decide_action(sensor: dict, risk: dict, event: dict | None) -> dict:
    """
    Decide movimiento en función de sensores, IA y evento aleatorio.
    """
    nivel = risk.get("nivel", "Desconocido")
    accion_ia = risk.get("accion", "Sin accion")
    bateria = parse_float(sensor.get("bateria"), 100.0)
    obstaculo = parse_float(sensor.get("obstaculo"), 5.0)
    gas = parse_float(sensor.get("gas"), 0.0)
    vibracion = parse_float(sensor.get("vib"), 0.0)
    persona = int(parse_float(sensor.get("persona"), 0.0))

    decision_reason = []
    decision_reason.append(f"IA={nivel}")
    decision_reason.append(f"accion_ia={accion_ia}")

    # Prioridades de seguridad.
    if bateria < 20:
        return {
            "linear": 0.15,
            "angular": random.choice([-0.65, 0.65]),
            "duration": 3.0,
            "decision": "Batería baja: volver a base o buscar ruta segura.",
            "alert": True,
        }

    if persona == 1:
        return {
            "linear": 0.0,
            "angular": 0.0,
            "duration": 2.0,
            "decision": "Persona detectada: detenerse y enviar alerta al equipo de rescate.",
            "alert": True,
        }

    if nivel == "Alto":
        return {
            "linear": 0.10,
            "angular": random.choice([-0.85, 0.85]),
            "duration": random.uniform(2.0, 4.0),
            "decision": "Riesgo alto: cambiar ruta o detener avance principal.",
            "alert": True,
        }

    if obstaculo < 1.0:
        return {
            "linear": 0.10,
            "angular": random.choice([-0.90, 0.90]),
            "duration": random.uniform(2.0, 3.5),
            "decision": "Obstáculo cercano: maniobra evasiva.",
            "alert": False,
        }

    if event is not None:
        event_type = event["type"]
        if event_type == "derrumbe_secundario":
            return {
                "linear": 0.12,
                "angular": random.choice([-0.75, 0.75]),
                "duration": random.uniform(2.0, 3.5),
                "decision": "Evento: derrumbe secundario. Reducir velocidad y cambiar orientación.",
                "alert": True,
            }

        if event_type == "obstaculo_inesperado":
            return {
                "linear": 0.15,
                "angular": random.choice([-0.80, 0.80]),
                "duration": random.uniform(2.0, 3.5),
                "decision": "Evento: obstáculo inesperado. Ejecutar evasión.",
                "alert": False,
            }

        if event_type == "humo_denso":
            return {
                "linear": 0.18,
                "angular": random.uniform(-0.25, 0.25),
                "duration": random.uniform(2.0, 4.0),
                "decision": "Evento: humo denso. Avanzar lentamente.",
                "alert": gas > 180,
            }

        if event_type == "perdida_comunicacion":
            return {
                "linear": 0.20,
                "angular": random.uniform(-0.20, 0.20),
                "duration": random.uniform(2.0, 3.0),
                "decision": "Evento: comunicación parcial. Reducir velocidad.",
                "alert": False,
            }

        if event_type == "ruido_de_victima":
            return {
                "linear": 0.25,
                "angular": random.uniform(-0.35, 0.35),
                "duration": random.uniform(2.0, 4.5),
                "decision": "Evento: posible víctima. Explorar con cautela.",
                "alert": True,
            }

    if nivel == "Medio" or gas > 160 or vibracion > 1.2:
        return {
            "linear": random.uniform(0.18, 0.38),
            "angular": random.uniform(-0.35, 0.35),
            "duration": random.uniform(2.0, 4.0),
            "decision": "Riesgo medio o sensores elevados: avanzar con precaución.",
            "alert": False,
        }

    # Riesgo bajo.
    return {
        "linear": random.uniform(0.45, 0.85),
        "angular": random.uniform(-0.20, 0.20),
        "duration": random.uniform(2.0, 5.0),
        "decision": "Riesgo bajo: avanzar explorando.",
        "alert": False,
    }


# ============================================================
# Reporte de misión
# ============================================================

def save_mission_log(records: list[dict], seed: int, success_reason: str) -> Path:
    MISSION_LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = MISSION_LOG_DIR / f"mission_{timestamp}.json"
    txt_path = MISSION_LOG_DIR / f"mission_{timestamp}.txt"

    risks = [record.get("risk", {}).get("nivel", "Desconocido") for record in records]
    alerts = sum(1 for record in records if record.get("decision", {}).get("alert"))

    risk_priority = {"Bajo": 1, "Medio": 2, "Alto": 3, "Desconocido": 0}
    max_risk = "Desconocido"
    if risks:
        max_risk = max(risks, key=lambda risk: risk_priority.get(risk, 0))

    final_record = records[-1] if records else {}
    final_sensor = final_record.get("sensor", {})
    final_risk = final_record.get("risk", {})

    mission_summary = {
        "timestamp": timestamp,
        "seed": seed,
        "steps": len(records),
        "max_risk": max_risk,
        "alerts": alerts,
        "final_sensor": final_sensor,
        "final_risk": final_risk,
        "success_reason": success_reason,
        "records": records,
    }

    json_path.write_text(json.dumps(mission_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("RESCUETWIN AI - BITÁCORA DE MISIÓN")
    lines.append("=" * 60)
    lines.append(f"Fecha/hora: {timestamp}")
    lines.append(f"Seed: {seed}")
    lines.append(f"Pasos ejecutados: {len(records)}")
    lines.append(f"Riesgo máximo detectado: {max_risk}")
    lines.append(f"Alertas generadas: {alerts}")
    lines.append(f"Resultado: {success_reason}")
    lines.append("")
    lines.append("Resumen final")
    lines.append("-" * 60)
    lines.append(f"Sensor final: {final_sensor.get('_raw', 'sin datos')}")
    lines.append(f"Riesgo final: {final_risk.get('_raw', 'sin datos')}")
    lines.append("")
    lines.append("Detalle paso a paso")
    lines.append("-" * 60)

    for record in records:
        lines.append(
            f"Paso {record['step']} | "
            f"Evento: {record.get('event_description', 'Sin evento')} | "
            f"Decisión: {record['decision']['decision']}"
        )
        lines.append(f"  Sensor: {record['sensor'].get('_raw', 'sin datos')}")
        lines.append(f"  Riesgo: {record['risk'].get('_raw', 'sin datos')}")
        lines.append(
            f"  Movimiento: v={record['decision']['linear']:.2f}, "
            f"w={record['decision']['angular']:.2f}, "
            f"duración={record['decision']['duration']:.1f}s"
        )
        lines.append("")

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    return txt_path


# ============================================================
# Misión
# ============================================================

def run_autonomous_mission(steps: int, event_probability: float, seed: int) -> None:
    print_title("MISIÓN AUTÓNOMA RESCUETWIN AI")

    records = []
    success_reason = "Misión finalizada por cantidad máxima de pasos."

    print_step("Lectura inicial")
    print(echo_once("/robot/status"))
    print(echo_once("/robot/sensor_status"))
    print(echo_once("/robot/risk_status"))

    for step in range(1, steps + 1):
        print_title(f"PASO DE MISIÓN {step} / {steps}")

        sensor = get_sensor_status()
        risk = get_risk_status()
        event = generate_random_event(event_probability)

        if event is not None:
            event_description = event["description"]
            print(f"EVENTO ALEATORIO: {event_description}")
        else:
            event_description = "Sin evento"
            print("EVENTO ALEATORIO: Sin evento")

        decision = decide_action(sensor, risk, event)

        print(f"Sensores: {sensor.get('_raw', 'sin datos')}")
        print(f"Riesgo IA: {risk.get('_raw', 'sin datos')}")
        print(f"Decisión autónoma: {decision['decision']}")
        print(
            f"Movimiento enviado: linear.x={decision['linear']:.2f}, "
            f"angular.z={decision['angular']:.2f}, "
            f"duración={decision['duration']:.1f}s"
        )

        publish_cmd(decision["linear"], decision["angular"])
        time.sleep(decision["duration"])

        stop_robot()
        time.sleep(1.5)

        updated_status = get_robot_status()
        updated_sensor = get_sensor_status()
        updated_risk = get_risk_status()

        print_step("Estado actualizado")
        print(updated_status.get("_raw", "sin datos"))

        print_step("Sensores actualizados")
        print(updated_sensor.get("_raw", "sin datos"))

        print_step("Riesgo actualizado")
        print(updated_risk.get("_raw", "sin datos"))

        record = {
            "step": step,
            "timestamp": now_str(),
            "event": event,
            "event_description": event_description,
            "status": updated_status,
            "sensor": updated_sensor,
            "risk": updated_risk,
            "decision": decision,
        }
        records.append(record)

        # Condiciones de cierre anticipado.
        persona = int(parse_float(updated_sensor.get("persona"), 0.0))
        bateria = parse_float(updated_sensor.get("bateria"), 100.0)
        nivel = updated_risk.get("nivel", "Desconocido")

        if persona == 1:
            success_reason = "Misión finalizada: posible víctima detectada y alerta enviada."
            print_title(success_reason)
            break

        if bateria < 15:
            success_reason = "Misión finalizada: batería crítica, retorno a base requerido."
            print_title(success_reason)
            break

        if nivel == "Alto" and decision["alert"]:
            # No cortamos siempre por riesgo alto; cortamos solo si se desea simular seguridad estricta.
            # Se deja continuar para mostrar más pasos, salvo que se acumulen varios altos.
            high_count = sum(1 for r in records if r.get("risk", {}).get("nivel") == "Alto")
            if high_count >= 3:
                success_reason = "Misión finalizada: riesgo alto sostenido, operación detenida por seguridad."
                print_title(success_reason)
                break

    log_path = save_mission_log(records, seed, success_reason)

    print_title("RESUMEN FINAL")
    print(f"Resultado: {success_reason}")
    print(f"Pasos ejecutados: {len(records)}")
    print(f"Bitácora generada en: {log_path}")


def cleanup() -> None:
    print_step("Deteniendo nodos de la misión")
    docker_exec("pkill -f 'motion_node|sensor_sim_node|risk_ai_node' || true", check=False)
    print("Misión finalizada.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta una misión autónoma de RescueTwin AI con ROS 2."
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=10,
        help="Cantidad máxima de pasos de la misión. Valor por defecto: 10.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla opcional para repetir una misión.",
    )
    parser.add_argument(
        "--event-probability",
        type=float,
        default=0.35,
        help="Probabilidad de evento aleatorio por paso. Valor por defecto: 0.35.",
    )
    parser.add_argument(
        "--skip-gazebo-check",
        action="store_true",
        help="Omite la validación headless del mundo Gazebo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.steps < 1:
        print("ERROR: --steps debe ser mayor o igual a 1.")
        sys.exit(1)

    if args.event_probability < 0 or args.event_probability > 1:
        print("ERROR: --event-probability debe estar entre 0 y 1.")
        sys.exit(1)

    seed = int(time.time()) if args.seed is None else args.seed
    random.seed(seed)

    print_title("RESCUETWIN AI - MISIÓN AUTÓNOMA")
    print(f"Seed usada: {seed}")
    print(f"Pasos máximos: {args.steps}")
    print(f"Probabilidad de evento: {args.event_probability}")

    try:
        check_docker()
        start_or_create_container()
        check_project_inside_container()
        check_python_versions()
        check_model_loads()
        build_workspace()

        if not args.skip_gazebo_check:
            validate_gazebo_world_headless()

        stop_previous_nodes()

        start_node_detached("motion_node")
        start_node_detached("sensor_sim_node")
        start_node_detached("risk_ai_node")

        wait_for_topic("/robot/status")
        wait_for_topic("/robot/sensor_status")
        wait_for_topic("/robot/risk_status")

        time.sleep(3)

        run_autonomous_mission(
            steps=args.steps,
            event_probability=args.event_probability,
            seed=seed,
        )

    except subprocess.CalledProcessError as exc:
        print("\nERROR ejecutando comando:")
        print(exc)
        if hasattr(exc, "stdout") and exc.stdout:
            print(exc.stdout)
        sys.exit(1)

    finally:
        cleanup()


if __name__ == "__main__":
    main()
