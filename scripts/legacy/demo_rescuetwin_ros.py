#!/usr/bin/env python3
"""
Demo automática ROS/Gazebo - RescueTwin AI

Este script levanta el contenedor Docker, compila el workspace ROS 2,
inicia los nodos principales del proyecto y ejecuta una demostración:

1. Valida que Docker esté disponible.
2. Levanta o crea el contenedor `rescuetwin_ros`.
3. Compila `ros2_ws`.
4. Inicia:
   - motion_node
   - sensor_sim_node
   - risk_ai_node
5. Mueve el robot simulado.
6. Consulta:
   - /robot/status
   - /robot/sensor_status
   - /robot/risk_status
7. Detiene los nodos al finalizar.

Ejecutar desde la raíz del proyecto:

    python3 demo_rescuetwin_ros.py

Requisitos:
- Docker Desktop abierto.
- Imagen Docker existente: rescuetwin_ros_image
- Contenedor o imagen con ROS 2 Humble.
- Modelos entrenados en:
    models/random_forest_rescuetwin.pkl
    models/model_columns.pkl
"""

import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CONTAINER_NAME = "rescuetwin_ros"
IMAGE_NAME = "rescuetwin_ros_image"
CONTAINER_PROJECT_DIR = "/workspace/RescueTwin-AI"
CONTAINER_WS_DIR = f"{CONTAINER_PROJECT_DIR}/ros2_ws"


def print_title(text: str) -> None:
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


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
    full_command = [
        "docker",
        "exec",
        CONTAINER_NAME,
        "bash",
        "-lc",
        command,
    ]

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


def check_docker() -> None:
    print_step("Verificando Docker")
    try:
        result = run_host(["docker", "ps"], capture=True)
        print(result.stdout.strip())
    except Exception:
        print(
            "\nERROR: Docker no está disponible.\n"
            "Abrí Docker Desktop y esperá a que quede corriendo. Después volvé a ejecutar este script."
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
            "Primero creá o recuperá la imagen usada para ROS/Gazebo.\n"
            "Podés verificar tus imágenes con:\n"
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
    ]

    for relative_path in required_paths:
        check_cmd = f"test -e {CONTAINER_PROJECT_DIR}/{relative_path}"
        result = docker_exec(check_cmd, check=False, capture=True)
        if result.returncode != 0:
            print(f"\nERROR: Falta el archivo o carpeta: {relative_path}")
            sys.exit(1)


def check_python_versions() -> None:
    print_step("Verificando librerías Python para el modelo IA")
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
            "Probablemente hay incompatibilidad de versiones de numpy/scipy/sklearn.\n"
            "Dentro del contenedor probá:\n\n"
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
        print("Advertencia: no se pudo confirmar la carga del mundo Gazebo, pero se continúa con la demo ROS.")


def stop_previous_nodes() -> None:
    print_step("Deteniendo nodos anteriores si quedaron corriendo")
    docker_exec("pkill -f 'motion_node|sensor_sim_node|risk_ai_node' || true", check=False)


def start_node_detached(node_name: str) -> None:
    print_step(f"Iniciando {node_name}")
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


def echo_once(topic: str, timeout_seconds: int = 10) -> str:
    command = ros_command(f"timeout {timeout_seconds}s ros2 topic echo {topic} --once")
    result = docker_exec(command, capture=True, check=False)
    return result.stdout.strip()


def publish_cmd(linear_x: float, angular_z: float) -> None:
    command = ros_command(
        "ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "
        f"\"{{linear: {{x: {linear_x}}}, angular: {{z: {angular_z}}}}}\""
    )
    docker_exec(command, capture=True, check=False)


def run_demo_sequence() -> None:
    print_title("DEMO RESCUETWIN AI - ROS 2 + Sensores + Modelo IA")

    print_step("Topics ROS disponibles")
    topics = docker_exec(ros_command("ros2 topic list"), capture=True)
    print(topics.stdout.strip())

    print_step("Estado inicial del robot")
    print(echo_once("/robot/status"))

    print_step("Sensores iniciales")
    print(echo_once("/robot/sensor_status"))

    print_step("Predicción IA inicial")
    print(echo_once("/robot/risk_status"))

    print_step("Movimiento 1: avanzar")
    publish_cmd(0.8, 0.0)
    time.sleep(4)
    publish_cmd(0.0, 0.0)
    time.sleep(2)

    print_step("Estado luego de avanzar")
    print(echo_once("/robot/status"))

    print_step("Sensores luego de avanzar")
    print(echo_once("/robot/sensor_status"))

    print_step("Predicción IA luego de avanzar")
    print(echo_once("/robot/risk_status"))

    print_step("Movimiento 2: avanzar girando")
    publish_cmd(0.4, 0.6)
    time.sleep(4)
    publish_cmd(0.0, 0.0)
    time.sleep(2)

    print_step("Estado luego de avanzar girando")
    print(echo_once("/robot/status"))

    print_step("Sensores luego de avanzar girando")
    print(echo_once("/robot/sensor_status"))

    print_step("Predicción IA final")
    print(echo_once("/robot/risk_status"))

    print_step("Nivel de riesgo separado")
    print(echo_once("/robot/nivel_riesgo"))

    print_step("Acción recomendada separada")
    print(echo_once("/robot/accion_recomendada"))


def cleanup() -> None:
    print_step("Deteniendo nodos de la demo")
    docker_exec("pkill -f 'motion_node|sensor_sim_node|risk_ai_node' || true", check=False)
    print("Demo finalizada.")


def main() -> None:
    print_title("RESCUETWIN AI - DEMO AUTOMÁTICA")

    try:
        check_docker()
        start_or_create_container()
        check_project_inside_container()
        check_python_versions()
        check_model_loads()
        build_workspace()
        validate_gazebo_world_headless()

        stop_previous_nodes()

        start_node_detached("motion_node")
        start_node_detached("sensor_sim_node")
        start_node_detached("risk_ai_node")

        wait_for_topic("/robot/status")
        wait_for_topic("/robot/sensor_status")
        wait_for_topic("/robot/risk_status")

        time.sleep(3)

        run_demo_sequence()

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
