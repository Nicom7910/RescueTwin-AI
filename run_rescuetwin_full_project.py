#!/usr/bin/env python3
"""
run_rescuetwin_full_project.py

Ejecutor automático completo para RescueTwin AI.

Este archivo permite levantar y demostrar el proyecto completo desde una sola ejecución:

1. Verifica Docker Desktop.
2. Levanta o crea el contenedor rescuetwin_ros.
3. Verifica estructura del proyecto.
4. Verifica librerías Python y modelo IA.
5. Compila ROS 2.
6. Valida Gazebo en modo headless.
7. Inicia automáticamente:
   - motion_node
   - sensor_sim_node
   - risk_ai_node
   - decision_node
   - mission_logger_node
8. Deja correr la misión autónoma.
9. Muestra estados, decisiones, alertas y logs.
10. Genera visualización 2D de la ruta.
11. Detiene los nodos al finalizar.

Ejecutar desde la raíz del proyecto:

    python3 run_rescuetwin_full_project.py

Opciones útiles:

    python3 run_rescuetwin_full_project.py --duration 60
    python3 run_rescuetwin_full_project.py --skip-gazebo-check
    python3 run_rescuetwin_full_project.py --no-stop
    python3 run_rescuetwin_full_project.py --no-plot

Notas:
- Docker Desktop debe estar abierto.
- Debe existir la imagen Docker: rescuetwin_ros_image.
- El proyecto debe estar en la carpeta donde se ejecuta este archivo.
"""

from __future__ import annotations

import argparse
import os
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

LOG_DIR = PROJECT_DIR / "reports" / "mission_logs"


# ============================================================
# Utilidades de impresión
# ============================================================

def title(text: str) -> None:
    print("\n" + "=" * 96)
    print(text)
    print("=" * 96)


def step(text: str) -> None:
    print(f"\n[+] {text}")


def warn(text: str) -> None:
    print(f"\n[ADVERTENCIA] {text}")


def error(text: str) -> None:
    print(f"\n[ERROR] {text}")


# ============================================================
# Ejecutores
# ============================================================

def run_host(command: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=check,
        )

    return subprocess.run(command, check=check)


def run_host_shell(command: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(
            command,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=check,
        )

    return subprocess.run(command, shell=True, check=check)


def docker_exec(command: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    full_command = [
        "docker",
        "exec",
        CONTAINER_NAME,
        "bash",
        "-lc",
        command,
    ]

    if capture:
        return subprocess.run(
            full_command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=check,
        )

    return subprocess.run(full_command, check=check)


def ros_command(command: str) -> str:
    return (
        "set +u && "
        "source /opt/ros/humble/setup.bash && "
        f"cd {CONTAINER_WS_DIR} && "
        "source install/setup.bash && "
        f"{command}"
    )


# ============================================================
# Docker
# ============================================================

def check_docker() -> None:
    step("Verificando Docker")

    result = run_host(["docker", "ps"], capture=True, check=False)

    if result.returncode != 0:
        error(
            "Docker no está disponible.\n"
            "Abrí Docker Desktop, esperá a que esté corriendo y volvé a ejecutar este script."
        )
        print(result.stdout)
        sys.exit(1)

    print(result.stdout.strip() or "Docker OK.")


def container_exists() -> bool:
    result = run_host_shell(
        f"docker ps -a --format '{{{{.Names}}}}' | grep -w {CONTAINER_NAME}",
        capture=True,
        check=False,
    )
    return result.returncode == 0


def container_running() -> bool:
    result = run_host_shell(
        f"docker ps --format '{{{{.Names}}}}' | grep -w {CONTAINER_NAME}",
        capture=True,
        check=False,
    )
    return result.returncode == 0


def image_exists() -> bool:
    result = run_host_shell(
        f"docker images --format '{{{{.Repository}}}}' | grep -w {IMAGE_NAME}",
        capture=True,
        check=False,
    )
    return result.returncode == 0


def start_or_create_container() -> None:
    step("Levantando contenedor Docker")

    if container_exists():
        if container_running():
            print(f"El contenedor {CONTAINER_NAME} ya está corriendo.")
        else:
            run_host(["docker", "start", CONTAINER_NAME])
            print(f"Contenedor {CONTAINER_NAME} iniciado.")
        return

    if not image_exists():
        error(
            f"No existe la imagen Docker {IMAGE_NAME}.\n"
            "Verificá tus imágenes con:\n"
            "    docker images\n\n"
            "Si venías trabajando en otro contenedor, primero guardalo como imagen:\n"
            "    docker commit <ID_CONTENEDOR> rescuetwin_ros_image"
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
    print(f"Contenedor {CONTAINER_NAME} creado e iniciado.")


# ============================================================
# Verificaciones
# ============================================================

def verify_project_structure() -> None:
    step("Verificando estructura del proyecto dentro del contenedor")

    result = docker_exec(f"cd {CONTAINER_PROJECT_DIR} && ls", capture=True, check=False)
    print(result.stdout.strip())

    required_paths = [
        "models/random_forest_rescuetwin.pkl",
        "models/model_columns.pkl",
        "ros2_ws/src/rescuetwin_sim",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/motion_node.py",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/sensor_sim_node.py",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/risk_ai_node.py",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/decision_node.py",
        "ros2_ws/src/rescuetwin_sim/rescuetwin_sim/mission_logger_node.py",
    ]

    missing = []

    for relative_path in required_paths:
        result = docker_exec(
            f"test -e {CONTAINER_PROJECT_DIR}/{relative_path}",
            capture=True,
            check=False,
        )
        if result.returncode != 0:
            missing.append(relative_path)

    if missing:
        error("Faltan archivos requeridos:")
        for item in missing:
            print(f" - {item}")

        print(
            "\nAsegurate de haber copiado los archivos de la Etapa 5:\n"
            "- decision_node.py\n"
            "- mission_logger_node.py\n"
            "y de haber modificado setup.py con sus entry_points."
        )
        sys.exit(1)


def verify_setup_py_entry_points() -> None:
    step("Verificando entry_points de setup.py")

    setup_path = f"{CONTAINER_PROJECT_DIR}/ros2_ws/src/rescuetwin_sim/setup.py"
    result = docker_exec(f"cat {setup_path}", capture=True, check=False)

    if result.returncode != 0:
        error("No se pudo leer setup.py")
        sys.exit(1)

    content = result.stdout

    required_entries = [
        "motion_node = rescuetwin_sim.motion_node:main",
        "sensor_sim_node = rescuetwin_sim.sensor_sim_node:main",
        "risk_ai_node = rescuetwin_sim.risk_ai_node:main",
        "decision_node = rescuetwin_sim.decision_node:main",
        "mission_logger_node = rescuetwin_sim.mission_logger_node:main",
    ]

    missing = [entry for entry in required_entries if entry not in content]

    if missing:
        error("Faltan entry_points en setup.py:")
        for entry in missing:
            print(f" - {entry}")
        print("\nAgregalos en setup.py dentro de console_scripts.")
        sys.exit(1)

    print("setup.py OK.")


def verify_python_and_model() -> None:
    step("Verificando librerías Python y carga del modelo IA")

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
        error(
            "No se pudo cargar el modelo IA.\n\n"
            "Solución sugerida dentro del contenedor:\n"
            "pip3 uninstall -y numpy scipy scikit-learn pandas joblib\n"
            "pip3 install --no-cache-dir numpy==2.2.6 scipy==1.15.3 scikit-learn==1.7.2 pandas==2.3.3 joblib==1.5.3"
        )
        sys.exit(1)


# ============================================================
# ROS build y Gazebo
# ============================================================

def build_ros_workspace() -> None:
    step("Compilando workspace ROS 2")

    command = (
        "set +u && "
        "source /opt/ros/humble/setup.bash && "
        f"cd {CONTAINER_WS_DIR} && "
        "rm -rf build install log && "
        "colcon build && "
        "source install/setup.bash && "
        "ros2 pkg list | grep rescuetwin_sim"
    )

    result = docker_exec(command, capture=True, check=False)
    print(result.stdout.strip())

    if result.returncode != 0:
        error("Falló la compilación de ROS 2.")
        sys.exit(1)


def validate_gazebo_headless() -> None:
    step("Validando Gazebo headless")

    command = (
        f"cd {CONTAINER_PROJECT_DIR} && "
        "timeout 5s gzserver ros2_ws/src/rescuetwin_sim/worlds/collapse_world.world --verbose"
    )

    result = docker_exec(command, capture=True, check=False)
    output = result.stdout.strip()

    print("\n".join(output.splitlines()[:25]))

    if "Loading world file" in output or "Connected to gazebo master" in output:
        print("Gazebo headless OK.")
    else:
        warn("No se confirmó Gazebo headless, pero se continúa con ROS.")


# ============================================================
# Nodos
# ============================================================

def stop_nodes() -> None:
    step("Deteniendo nodos previos")
    docker_exec(
        "pkill -f 'motion_node|sensor_sim_node|risk_ai_node|decision_node|mission_logger_node' || true",
        check=False,
    )


def start_node(node_name: str) -> None:
    step(f"Iniciando {node_name}")

    log_path = f"/tmp/{node_name}.log"
    command = ros_command(
        f"nohup ros2 run rescuetwin_sim {node_name} > {log_path} 2>&1 &"
    )

    result = docker_exec(command, capture=True, check=False)

    if result.returncode != 0:
        error(f"No se pudo iniciar {node_name}")
        print(result.stdout)
        sys.exit(1)

    time.sleep(1.8)

    log = docker_exec(f"tail -n 20 {log_path} || true", capture=True, check=False)
    if log.stdout.strip():
        print(log.stdout.strip())


def start_all_nodes() -> None:
    start_node("motion_node")
    start_node("sensor_sim_node")
    start_node("risk_ai_node")
    start_node("decision_node")
    start_node("mission_logger_node")


def wait_for_topic(topic: str, timeout_seconds: int = 20) -> None:
    step(f"Esperando topic {topic}")

    start = time.time()

    while time.time() - start < timeout_seconds:
        result = docker_exec(ros_command("ros2 topic list"), capture=True, check=False)
        if topic in result.stdout:
            print(f"Topic disponible: {topic}")
            return
        time.sleep(1)

    warn(f"No apareció el topic {topic} dentro de {timeout_seconds} segundos.")


def wait_for_required_topics() -> None:
    topics = [
        "/robot/status",
        "/robot/sensor_status",
        "/robot/risk_status",
        "/mission/state",
        "/mission/current_objective",
        "/mission/decision_status",
        "/mission/log_status",
        "/base/alertas",
    ]

    for topic in topics:
        wait_for_topic(topic)


# ============================================================
# Lecturas ROS
# ============================================================

def echo_once(topic: str, timeout_seconds: int = 8) -> str:
    result = docker_exec(
        ros_command(f"timeout {timeout_seconds}s ros2 topic echo {topic} --once"),
        capture=True,
        check=False,
    )
    return result.stdout.strip() or "(sin datos)"


def show_snapshot(label: str) -> None:
    title(label)

    print("\n--- Estado del robot ---")
    print(echo_once("/robot/status"))

    print("\n--- Sensores ---")
    print(echo_once("/robot/sensor_status"))

    print("\n--- Riesgo IA ---")
    print(echo_once("/robot/risk_status"))

    print("\n--- Estado de misión ---")
    print(echo_once("/mission/state"))

    print("\n--- Objetivo actual ---")
    print(echo_once("/mission/current_objective"))

    print("\n--- Decisión autónoma ---")
    print(echo_once("/mission/decision_status"))

    print("\n--- Última alerta base ---")
    print(echo_once("/base/alertas", timeout_seconds=4))

    print("\n--- Logger ---")
    print(echo_once("/mission/log_status"))


def run_mission(duration_seconds: int, snapshots: int) -> None:
    title("MISIÓN AUTÓNOMA EN EJECUCIÓN")

    if duration_seconds < 5:
        duration_seconds = 5

    if snapshots < 1:
        snapshots = 1

    interval = max(5, duration_seconds // snapshots)

    start_time = time.time()
    next_snapshot = 0
    snapshot_count = 0

    while time.time() - start_time < duration_seconds:
        elapsed = int(time.time() - start_time)

        if elapsed >= next_snapshot and snapshot_count < snapshots:
            show_snapshot(f"LECTURA DE MISIÓN {snapshot_count + 1} / {snapshots} - t={elapsed}s")
            snapshot_count += 1
            next_snapshot += interval

        time.sleep(1)

    show_snapshot("LECTURA FINAL DE MISIÓN")


# ============================================================
# Logs y visualización
# ============================================================

def latest_mission_csv() -> Path | None:
    if not LOG_DIR.exists():
        return None

    files = sorted(
        LOG_DIR.glob("ros_mission_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return files[0] if files else None


def generate_2d_plot() -> None:
    step("Generando visualización 2D de la ruta")

    visualizer = PROJECT_DIR / "scripts" / "visualize_mission_route.py"

    if not visualizer.exists():
        warn(
            "No existe scripts/visualize_mission_route.py.\n"
            "Copialo desde los archivos de Etapa 5."
        )
        return

    csv_path = latest_mission_csv()

    if csv_path is None:
        warn("No se encontró ningún CSV en reports/mission_logs. No se puede graficar.")
        return

    result = run_host(
        [sys.executable, str(visualizer), str(csv_path)],
        capture=True,
        check=False,
    )

    print(result.stdout.strip())

    if result.returncode != 0:
        warn(
            "No se pudo generar la visualización 2D.\n"
            "Puede faltar matplotlib/pandas en el entorno de Mac.\n"
            "Instalá con:\n"
            "    pip install matplotlib pandas"
        )


def show_generated_files() -> None:
    step("Archivos generados")

    if not LOG_DIR.exists():
        warn("Todavía no existe reports/mission_logs.")
        return

    files = sorted(LOG_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

    for file in files[:10]:
        print(file)


# ============================================================
# Args / main
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Levanta y ejecuta automáticamente el proyecto completo RescueTwin AI."
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=45,
        help="Duración de la misión en segundos. Default: 45.",
    )

    parser.add_argument(
        "--snapshots",
        type=int,
        default=4,
        help="Cantidad de lecturas mostradas durante la misión. Default: 4.",
    )

    parser.add_argument(
        "--skip-gazebo-check",
        action="store_true",
        help="Omite la validación de Gazebo headless.",
    )

    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="No genera visualización 2D al finalizar.",
    )

    parser.add_argument(
        "--no-stop",
        action="store_true",
        help="No detiene los nodos al finalizar, útil para inspeccionar topics manualmente.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    title("RESCUETWIN AI - EJECUCIÓN COMPLETA AUTOMÁTICA")
    print(f"Proyecto: {PROJECT_DIR}")
    print(f"Duración misión: {args.duration}s")
    print(f"Snapshots: {args.snapshots}")
    print(f"Hora inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        check_docker()
        start_or_create_container()

        verify_project_structure()
        verify_setup_py_entry_points()
        verify_python_and_model()

        build_ros_workspace()

        if not args.skip_gazebo_check:
            validate_gazebo_headless()

        stop_nodes()
        start_all_nodes()
        wait_for_required_topics()

        # Pequeña espera para que todos los nodos publiquen primeros mensajes.
        time.sleep(4)

        run_mission(duration_seconds=args.duration, snapshots=args.snapshots)

        if not args.no_plot:
            generate_2d_plot()

        show_generated_files()

        title("EJECUCIÓN FINALIZADA")
        print("El sistema completo fue ejecutado correctamente.")
        print("Revisá los archivos en reports/mission_logs/.")

    except KeyboardInterrupt:
        warn("Ejecución interrumpida por el usuario.")

    except subprocess.CalledProcessError as exc:
        error("Falló un comando del sistema.")
        print(exc)
        if getattr(exc, "stdout", None):
            print(exc.stdout)
        sys.exit(1)

    finally:
        if args.no_stop:
            warn(
                "Se dejaron los nodos corriendo por uso de --no-stop.\n"
                "Para detenerlos manualmente:\n"
                "docker exec rescuetwin_ros bash -lc \"pkill -f 'motion_node|sensor_sim_node|risk_ai_node|decision_node|mission_logger_node'\""
            )
        else:
            stop_nodes()


if __name__ == "__main__":
    main()
