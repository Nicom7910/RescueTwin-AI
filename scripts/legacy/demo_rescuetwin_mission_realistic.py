#!/usr/bin/env python3
"""
Misión realista RescueTwin AI - ROS 2 + Gazebo headless + IA

Esta versión busca que la demo se parezca más a una misión real de rescate:

- El robot no se mueve completamente al azar.
- Sigue una ruta de búsqueda con waypoints hacia una zona de posible víctima.
- Lee sensores reales de los topics ROS simulados.
- Lee el riesgo IA del modelo Random Forest.
- Toma decisiones automáticas según riesgo, batería, obstáculos, gas y eventos.
- Inyecta eventos de emergencia en los sensores ROS para que el modelo IA reaccione.
- Genera bitácoras TXT, JSON y CSV en reports/mission_logs/.

Uso básico:

    python3 demo_rescuetwin_mission_realistic.py

Opciones:

    python3 demo_rescuetwin_mission_realistic.py --steps 15
    python3 demo_rescuetwin_mission_realistic.py --steps 15 --seed 42
    python3 demo_rescuetwin_mission_realistic.py --event-probability 0.45
    python3 demo_rescuetwin_mission_realistic.py --skip-gazebo-check

Importante:
- Docker Desktop debe estar abierto.
- La imagen debe existir: rescuetwin_ros_image.
- El contenedor usado será: rescuetwin_ros.
- El proyecto se monta en: /workspace/RescueTwin-AI.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
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


# Ruta lógica de misión dentro del derrumbe.
# Está alineada con el mundo Gazebo que ya armaron:
# - entrada cerca de x=-4, y=0
# - zona crítica cerca de x=5, y=2.8
# - víctima simulada cerca de x=7, y=2.6
WAYPOINTS = [
    {"name": "Entrada del edificio", "x": -3.0, "y": 0.0},
    {"name": "Pasillo principal", "x": -1.0, "y": 0.2},
    {"name": "Zona de escombros inicial", "x": 1.5, "y": 0.8},
    {"name": "Cruce inestable", "x": 3.2, "y": 1.4},
    {"name": "Borde de zona crítica", "x": 4.7, "y": 2.0},
    {"name": "Zona probable de víctima", "x": 6.8, "y": 2.6},
]


# ============================================================
# Impresión
# ============================================================

def print_title(text: str) -> None:
    print("\n" + "=" * 96)
    print(text)
    print("=" * 96)


def print_step(text: str) -> None:
    print(f"\n[+] {text}")


def print_kv(label: str, value: str) -> None:
    print(f"{label:<24} {value}")


# ============================================================
# Ejecución de comandos
# ============================================================

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
# Docker / ROS setup
# ============================================================

def check_docker() -> None:
    print_step("Verificando Docker")
    try:
        result = run_host(["docker", "ps"], capture=True)
        print(result.stdout.strip())
    except Exception:
        print(
            "\nERROR: Docker no está disponible.\n"
            "Abrí Docker Desktop y esperá a que quede corriendo. Luego ejecutá nuevamente este script."
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
            "Verificá tus imágenes con:\n"
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
    print_step("Verificando estructura del proyecto")

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
        result = docker_exec(f"test -e {CONTAINER_PROJECT_DIR}/{relative_path}", check=False, capture=True)
        if result.returncode != 0:
            print(f"\nERROR: Falta el archivo/carpeta requerido: {relative_path}")
            sys.exit(1)


def check_python_versions_and_model() -> None:
    print_step("Verificando librerías Python y carga del modelo IA")

    command = (
        f"cd {CONTAINER_PROJECT_DIR} && "
        "python3 - << 'PY'\n"
        "import numpy, scipy, sklearn, pandas, joblib\n"
        "print('numpy', numpy.__version__)\n"
        "print('scipy', scipy.__version__)\n"
        "print('sklearn', sklearn.__version__)\n"
        "print('pandas', pandas.__version__)\n"
        "print('joblib', joblib.__version__)\n"
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
            "\nERROR: El modelo o las librerías no pudieron cargarse.\n"
            "Dentro del contenedor corregí versiones con:\n\n"
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

    print("\n".join(output.splitlines()[:20]))

    if "Loading world file" in output or "Connected to gazebo master" in output:
        print("Mundo Gazebo validado correctamente.")
    else:
        print("Advertencia: no se pudo confirmar la carga del mundo Gazebo, pero la misión ROS continuará.")


def stop_previous_nodes() -> None:
    print_step("Deteniendo nodos previos")
    docker_exec("pkill -f 'motion_node|sensor_sim_node|risk_ai_node' || true", check=False)


def start_node_detached(node_name: str) -> None:
    print_step(f"Iniciando {node_name}")
    docker_exec(ros_command(f"nohup ros2 run rescuetwin_sim {node_name} > /tmp/{node_name}.log 2>&1 &"))
    time.sleep(1.5)

    log = docker_exec(f"tail -n 20 /tmp/{node_name}.log || true", capture=True, check=False)
    if log.stdout.strip():
        print(log.stdout.strip())


def wait_for_topic(topic: str, timeout_seconds: int = 15) -> None:
    print_step(f"Esperando topic {topic}")

    start = time.time()
    while time.time() - start < timeout_seconds:
        result = docker_exec(ros_command("ros2 topic list"), capture=True, check=False)
        if topic in result.stdout:
            print(f"Topic disponible: {topic}")
            return
        time.sleep(1)

    print(f"Advertencia: no apareció el topic {topic}")


# ============================================================
# ROS IO
# ============================================================

def echo_once(topic: str, timeout_seconds: int = 10) -> str:
    result = docker_exec(ros_command(f"timeout {timeout_seconds}s ros2 topic echo {topic} --once"), capture=True, check=False)
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


def inject_float_sensor(topic: str, value: float, rate: int = 8, times: int = 16) -> None:
    """
    Inyecta un valor temporal en un sensor ROS.
    Esto permite simular eventos de emergencia que afectan realmente los topics
    consumidos por risk_ai_node.
    """
    command = ros_command(
        f"nohup ros2 topic pub -r {rate} --times {times} {topic} std_msgs/msg/Float32 "
        f"\"{{data: {value:.3f}}}\" > /tmp/inject_{topic.replace('/', '_')}.log 2>&1 &"
    )
    docker_exec(command, capture=True, check=False)


def inject_int_sensor(topic: str, value: int, rate: int = 8, times: int = 16) -> None:
    command = ros_command(
        f"nohup ros2 topic pub -r {rate} --times {times} {topic} std_msgs/msg/Int32 "
        f"\"{{data: {value}}}\" > /tmp/inject_{topic.replace('/', '_')}.log 2>&1 &"
    )
    docker_exec(command, capture=True, check=False)


# ============================================================
# Parsing
# ============================================================

def extract_string_data(echo_output: str) -> str:
    for line in echo_output.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return line.replace("data:", "", 1).strip()
    return echo_output.strip()


def parse_key_value_status(text: str) -> dict:
    clean = extract_string_data(text)
    clean = clean.replace(",", " |")
    parts = [part.strip() for part in clean.split("|")]

    data = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()

    data["_raw"] = clean
    return data


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default

    match = re.search(r"-?\d+(\.\d+)?", value)
    if match is None:
        return default

    return float(match.group(0))


def get_robot_status() -> dict:
    return parse_key_value_status(echo_once("/robot/status"))


def get_sensor_status() -> dict:
    return parse_key_value_status(echo_once("/robot/sensor_status"))


def get_risk_status() -> dict:
    return parse_key_value_status(echo_once("/robot/risk_status"))


# ============================================================
# Navegación y eventos
# ============================================================

def normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def current_waypoint_index(status: dict) -> int:
    x = parse_float(status.get("x"), -4.0)
    y = parse_float(status.get("y"), 0.0)

    # Selecciona el primer waypoint que no esté cerca.
    for index, waypoint in enumerate(WAYPOINTS):
        distance = math.dist((x, y), (waypoint["x"], waypoint["y"]))
        if distance > 1.0:
            return index

    return len(WAYPOINTS) - 1


def navigation_command_to_waypoint(status: dict, waypoint: dict, max_speed: float) -> tuple[float, float, float]:
    x = parse_float(status.get("x"), -4.0)
    y = parse_float(status.get("y"), 0.0)
    theta = parse_float(status.get("theta"), 0.0)

    dx = waypoint["x"] - x
    dy = waypoint["y"] - y
    distance = math.sqrt(dx * dx + dy * dy)
    desired_theta = math.atan2(dy, dx)
    angle_error = normalize_angle(desired_theta - theta)

    angular = max(-0.9, min(0.9, 1.2 * angle_error))
    linear = min(max_speed, max(0.10, 0.35 * distance))

    # Si está muy mal orientado, primero gira más y avanza menos.
    if abs(angle_error) > 1.0:
        linear = 0.08

    duration = random.uniform(2.0, 3.8)

    return linear, angular, duration


def generate_event(event_probability: float, step: int) -> dict | None:
    if random.random() > event_probability:
        return None

    events = [
        {
            "type": "gas_leak",
            "description": "Fuga de gas detectada: aumento temporal de gas_ppm.",
            "severity": "alta",
            "inject": lambda: inject_float_sensor("/robot/gas_ppm", random.uniform(280, 420)),
        },
        {
            "type": "secondary_collapse",
            "description": "Derrumbe secundario: vibración e inclinación aumentan.",
            "severity": "alta",
            "inject": lambda: (
                inject_float_sensor("/robot/vibracion", random.uniform(1.8, 2.4)),
                inject_float_sensor("/robot/inclinacion", random.uniform(22, 34)),
            ),
        },
        {
            "type": "unexpected_obstacle",
            "description": "Obstáculo inesperado cerca del robot.",
            "severity": "media",
            "inject": lambda: inject_float_sensor("/robot/distancia_obstaculo", random.uniform(0.25, 0.85)),
        },
        {
            "type": "dense_smoke",
            "description": "Humo denso: sube gas y baja seguridad operativa.",
            "severity": "media",
            "inject": lambda: inject_float_sensor("/robot/gas_ppm", random.uniform(160, 260)),
        },
        {
            "type": "victim_signal",
            "description": "Posible señal de víctima: se activa persona_detectada temporalmente.",
            "severity": "alta",
            "inject": lambda: inject_int_sensor("/robot/persona_detectada", 1),
        },
    ]

    # Evita que la víctima aparezca demasiado temprano siempre.
    candidate_events = events
    if step < 4:
        candidate_events = [e for e in events if e["type"] != "victim_signal"]

    event = random.choice(candidate_events)
    event["inject"]()
    return event


def decide_movement(status: dict, sensor: dict, risk: dict, event: dict | None) -> dict:
    nivel = risk.get("nivel", "Desconocido")
    accion_ia = risk.get("accion", "Sin accion")

    bateria = parse_float(sensor.get("bateria"), 100.0)
    obstaculo = parse_float(sensor.get("obstaculo"), 5.0)
    gas = parse_float(sensor.get("gas"), 0.0)
    vibracion = parse_float(sensor.get("vib"), 0.0)
    persona = int(parse_float(sensor.get("persona"), 0.0))

    wp_index = current_waypoint_index(status)
    waypoint = WAYPOINTS[wp_index]

    if persona == 1:
        return {
            "linear": 0.0,
            "angular": 0.0,
            "duration": 2.0,
            "decision": "Posible víctima detectada: detener robot y enviar alerta.",
            "mode": "rescue_alert",
            "waypoint": waypoint,
            "alert": True,
        }

    if bateria < 20:
        # Regreso aproximado a la entrada.
        base = WAYPOINTS[0]
        linear, angular, duration = navigation_command_to_waypoint(status, base, max_speed=0.25)
        return {
            "linear": linear,
            "angular": angular,
            "duration": duration,
            "decision": "Batería baja: iniciar retorno a la entrada.",
            "mode": "return_to_base",
            "waypoint": base,
            "alert": True,
        }

    if nivel == "Alto" or gas > 260 or vibracion > 1.7:
        return {
            "linear": random.uniform(0.05, 0.15),
            "angular": random.choice([-0.85, 0.85]),
            "duration": random.uniform(2.0, 3.5),
            "decision": "Riesgo alto o sensor crítico: cambiar orientación y evitar zona.",
            "mode": "avoid_high_risk",
            "waypoint": waypoint,
            "alert": True,
        }

    if obstaculo < 1.0:
        return {
            "linear": random.uniform(0.05, 0.18),
            "angular": random.choice([-0.95, 0.95]),
            "duration": random.uniform(2.0, 3.0),
            "decision": "Obstáculo cercano: ejecutar maniobra evasiva.",
            "mode": "avoid_obstacle",
            "waypoint": waypoint,
            "alert": False,
        }

    if event is not None and event["type"] in {"secondary_collapse", "unexpected_obstacle"}:
        return {
            "linear": random.uniform(0.08, 0.22),
            "angular": random.choice([-0.75, 0.75]),
            "duration": random.uniform(2.0, 3.5),
            "decision": f"Evento {event['type']}: reducir velocidad y cambiar ruta.",
            "mode": "event_response",
            "waypoint": waypoint,
            "alert": event["severity"] == "alta",
        }

    if nivel == "Medio" or gas > 150:
        linear, angular, duration = navigation_command_to_waypoint(status, waypoint, max_speed=0.35)
        return {
            "linear": linear,
            "angular": angular,
            "duration": duration,
            "decision": "Riesgo medio: avanzar hacia waypoint con precaución.",
            "mode": "cautious_navigation",
            "waypoint": waypoint,
            "alert": False,
        }

    linear, angular, duration = navigation_command_to_waypoint(status, waypoint, max_speed=0.75)
    return {
        "linear": linear,
        "angular": angular,
        "duration": duration,
        "decision": "Riesgo bajo: navegar hacia el siguiente waypoint.",
        "mode": "normal_navigation",
        "waypoint": waypoint,
        "alert": False,
        "accion_ia": accion_ia,
    }


# ============================================================
# Logging
# ============================================================

def save_logs(records: list[dict], seed: int, result: str) -> Path:
    MISSION_LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = MISSION_LOG_DIR / f"mission_realistic_{timestamp}.txt"
    json_path = MISSION_LOG_DIR / f"mission_realistic_{timestamp}.json"
    csv_path = MISSION_LOG_DIR / f"mission_realistic_{timestamp}.csv"

    risk_priority = {"Bajo": 1, "Medio": 2, "Alto": 3, "Desconocido": 0}
    risks = [r.get("risk", {}).get("nivel", "Desconocido") for r in records]
    max_risk = max(risks, key=lambda item: risk_priority.get(item, 0)) if risks else "Desconocido"
    alerts = sum(1 for r in records if r.get("decision", {}).get("alert"))

    summary = {
        "timestamp": timestamp,
        "seed": seed,
        "result": result,
        "steps": len(records),
        "max_risk": max_risk,
        "alerts": alerts,
        "records": records,
    }

    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "step", "time", "x", "y", "theta", "risk", "action_ai",
            "temperature", "gas", "vibration", "inclination", "battery",
            "obstacle", "person", "event", "decision", "mode", "linear", "angular", "duration"
        ])

        for r in records:
            status = r.get("status", {})
            sensor = r.get("sensor", {})
            risk = r.get("risk", {})
            decision = r.get("decision", {})
            event = r.get("event") or {}

            writer.writerow([
                r.get("step"),
                r.get("timestamp"),
                parse_float(status.get("x"), 0.0),
                parse_float(status.get("y"), 0.0),
                parse_float(status.get("theta"), 0.0),
                risk.get("nivel", "Desconocido"),
                risk.get("accion", ""),
                parse_float(sensor.get("temp"), 0.0),
                parse_float(sensor.get("gas"), 0.0),
                parse_float(sensor.get("vib"), 0.0),
                parse_float(sensor.get("inc"), 0.0),
                parse_float(sensor.get("bateria"), 0.0),
                parse_float(sensor.get("obstaculo"), 0.0),
                parse_float(sensor.get("persona"), 0.0),
                event.get("type", "sin_evento"),
                decision.get("decision", ""),
                decision.get("mode", ""),
                decision.get("linear", 0.0),
                decision.get("angular", 0.0),
                decision.get("duration", 0.0),
            ])

    lines = []
    lines.append("RESCUETWIN AI - BITÁCORA DE MISIÓN REALISTA")
    lines.append("=" * 72)
    lines.append(f"Fecha/hora: {timestamp}")
    lines.append(f"Seed: {seed}")
    lines.append(f"Resultado: {result}")
    lines.append(f"Pasos ejecutados: {len(records)}")
    lines.append(f"Riesgo máximo: {max_risk}")
    lines.append(f"Alertas generadas: {alerts}")
    lines.append("")
    lines.append("Ruta lógica de misión:")
    for idx, wp in enumerate(WAYPOINTS, start=1):
        lines.append(f"  {idx}. {wp['name']} -> x={wp['x']}, y={wp['y']}")
    lines.append("")
    lines.append("Detalle paso a paso")
    lines.append("-" * 72)

    for r in records:
        event = r.get("event")
        event_text = event["description"] if event else "Sin evento"
        decision = r.get("decision", {})
        wp = decision.get("waypoint", {})

        lines.append(f"Paso {r['step']} | {r['timestamp']}")
        lines.append(f"  Waypoint objetivo: {wp.get('name', 'N/D')}")
        lines.append(f"  Evento: {event_text}")
        lines.append(f"  Estado: {r.get('status', {}).get('_raw', 'sin datos')}")
        lines.append(f"  Sensores: {r.get('sensor', {}).get('_raw', 'sin datos')}")
        lines.append(f"  IA: {r.get('risk', {}).get('_raw', 'sin datos')}")
        lines.append(f"  Decisión: {decision.get('decision')}")
        lines.append(
            f"  Comando: v={decision.get('linear', 0):.2f}, "
            f"w={decision.get('angular', 0):.2f}, "
            f"duración={decision.get('duration', 0):.1f}s"
        )
        lines.append("")

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print_step("Archivos de bitácora generados")
    print(txt_path)
    print(json_path)
    print(csv_path)

    return txt_path


# ============================================================
# Misión
# ============================================================

def run_mission(steps: int, event_probability: float, seed: int) -> None:
    print_title("MISIÓN REALISTA RESCUETWIN AI")

    records = []
    result = "Misión finalizada por cantidad máxima de pasos."

    for step in range(1, steps + 1):
        print_title(f"PASO {step} / {steps}")

        status_before = get_robot_status()
        sensor_before = get_sensor_status()
        risk_before = get_risk_status()

        event = generate_event(event_probability, step)
        if event:
            print_kv("Evento", event["description"])
            # Espera breve para que risk_ai_node reciba los sensores inyectados.
            time.sleep(1.2)
            sensor_before = get_sensor_status()
            risk_before = get_risk_status()
        else:
            print_kv("Evento", "Sin evento")

        decision = decide_movement(status_before, sensor_before, risk_before, event)

        waypoint = decision.get("waypoint", {})
        print_kv("Waypoint objetivo", waypoint.get("name", "N/D"))
        print_kv("Estado inicial", status_before.get("_raw", "sin datos"))
        print_kv("Sensores", sensor_before.get("_raw", "sin datos"))
        print_kv("Riesgo IA", risk_before.get("_raw", "sin datos"))
        print_kv("Decisión", decision["decision"])
        print_kv("Modo", decision["mode"])
        print_kv("Comando", f"v={decision['linear']:.2f}, w={decision['angular']:.2f}, t={decision['duration']:.1f}s")

        publish_cmd(decision["linear"], decision["angular"])
        time.sleep(decision["duration"])
        stop_robot()
        time.sleep(1.3)

        status_after = get_robot_status()
        sensor_after = get_sensor_status()
        risk_after = get_risk_status()

        print_step("Lectura posterior al movimiento")
        print(status_after.get("_raw", "sin datos"))
        print(sensor_after.get("_raw", "sin datos"))
        print(risk_after.get("_raw", "sin datos"))

        event_log = None
        if event is not None:
            event_log = {
                "type": event.get("type"),
                "description": event.get("description"),
                "severity": event.get("severity"),
            }

        record = {
            "step": step,
            "timestamp": now_str(),
            "event": event_log,
            "status": status_after,
            "sensor": sensor_after,
            "risk": risk_after,
            "decision": decision,
        }
        records.append(record)

        persona = int(parse_float(sensor_after.get("persona"), 0.0))
        bateria = parse_float(sensor_after.get("bateria"), 100.0)
        nivel = risk_after.get("nivel", "Desconocido")

        if persona == 1:
            result = "Misión finalizada: posible víctima detectada y alerta enviada."
            print_title(result)
            break

        if bateria < 15:
            result = "Misión finalizada: batería crítica, retorno requerido."
            print_title(result)
            break

        high_count = sum(1 for r in records if r.get("risk", {}).get("nivel") == "Alto")
        if nivel == "Alto" and high_count >= 3:
            result = "Misión finalizada: riesgo alto sostenido, operación detenida por seguridad."
            print_title(result)
            break

    save_logs(records, seed, result)

    print_title("RESUMEN FINAL")
    print_kv("Resultado", result)
    print_kv("Pasos ejecutados", str(len(records)))
    if records:
        print_kv("Riesgo final", records[-1].get("risk", {}).get("_raw", "sin datos"))
        print_kv("Sensores finales", records[-1].get("sensor", {}).get("_raw", "sin datos"))


def cleanup() -> None:
    print_step("Deteniendo nodos")
    docker_exec("pkill -f 'motion_node|sensor_sim_node|risk_ai_node' || true", check=False)
    print("Demo finalizada.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta una misión realista RescueTwin AI.")
    parser.add_argument("--steps", type=int, default=12, help="Cantidad máxima de pasos. Default: 12.")
    parser.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad.")
    parser.add_argument("--event-probability", type=float, default=0.40, help="Probabilidad de evento por paso. Default: 0.40.")
    parser.add_argument("--skip-gazebo-check", action="store_true", help="Omite validación headless de Gazebo.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.steps < 1:
        print("ERROR: --steps debe ser mayor o igual a 1.")
        sys.exit(1)

    if not 0 <= args.event_probability <= 1:
        print("ERROR: --event-probability debe estar entre 0 y 1.")
        sys.exit(1)

    seed = int(time.time()) if args.seed is None else args.seed
    random.seed(seed)

    print_title("RESCUETWIN AI - MISIÓN REALISTA")
    print_kv("Seed", str(seed))
    print_kv("Pasos máximos", str(args.steps))
    print_kv("Probabilidad evento", str(args.event_probability))

    try:
        check_docker()
        start_or_create_container()
        check_project_inside_container()
        check_python_versions_and_model()
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

        run_mission(args.steps, args.event_probability, seed)

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
