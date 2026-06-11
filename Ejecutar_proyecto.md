## Ejecución rápida

El archivo principal para levantar todo el sistema es:

```bash
python3 run_rescuetwin_full_project.py
```

Ese script se encarga de:

```text
1. Verificar Docker
2. Levantar el contenedor ROS
3. Validar el modelo IA
4. Compilar ROS 2
5. Validar Gazebo en modo headless
6. Iniciar todos los nodos ROS
7. Ejecutar la misión autónoma
8. Generar logs de misión
9. Generar visualización 2D de la ruta
```

---

## 1. Requisitos previos

Antes de correr el proyecto, tener instalado:

- Python 3
- Git
- Docker Desktop
- VS Code o editor similar

También se necesita tener creada la imagen Docker:

```text
rescuetwin_ros_image
```

Y el contenedor usado por el proyecto será:

```text
rescuetwin_ros
```

---

## 2. Clonar o actualizar el proyecto

Si todavía no está clonado:

```bash
cd /Users/nicom7910/Downloads
git clone https://github.com/Nicom7910/RescueTwin-AI.git
cd RescueTwin-AI
```

Si ya existe localmente:

```bash
cd /Users/nicom7910/Downloads/RescueTwin-AI
git pull
```

---

## 3. Crear entorno virtual local

Desde la raíz del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si faltan dependencias para reportes, dashboard o tests:

```bash
pip install tabulate pytest matplotlib pandas streamlit
```

---

## 4. Abrir Docker Desktop

Abrir Docker Desktop y esperar a que esté corriendo.

Verificar:

```bash
docker ps
```

Si no aparece error, Docker está funcionando.

---

## 5. Levantar todo el sistema

Desde la raíz del proyecto:

```bash
cd /Users/nicom7910/Downloads/RescueTwin-AI
source .venv/bin/activate
python3 run_rescuetwin_full_project.py
```

Este comando levanta automáticamente el sistema completo.

Opciones útiles:

```bash
python3 run_rescuetwin_full_project.py --duration 60
```

```bash
python3 run_rescuetwin_full_project.py --duration 90 --snapshots 6
```

```bash
python3 run_rescuetwin_full_project.py --skip-gazebo-check
```

```bash
python3 run_rescuetwin_full_project.py --no-stop
```

La opción `--no-stop` deja los nodos corriendo para poder inspeccionar topics manualmente.

---

## 6. Qué se levanta automáticamente

El script principal inicia estos nodos ROS:

```text
motion_node
sensor_sim_node
risk_ai_node
decision_node
mission_logger_node
```

### motion_node

Simula el movimiento del robot.

Publica:

```text
/robot/pose
/robot/status
```

Lee:

```text
/robot/cmd_vel
```

### sensor_sim_node

Simula sensores ambientales y operativos.

Publica:

```text
/robot/temperatura
/robot/gas_ppm
/robot/vibracion
/robot/inclinacion
/robot/bateria
/robot/distancia_obstaculo
/robot/persona_detectada
/robot/sensor_status
```

### risk_ai_node

Carga el modelo IA y predice el nivel de riesgo.

Publica:

```text
/robot/nivel_riesgo
/robot/accion_recomendada
/robot/risk_status
```

### decision_node

Toma decisiones autónomas durante la misión.

Publica:

```text
/robot/cmd_vel
/base/alertas
/mission/state
/mission/current_objective
/mission/decision_status
```

### mission_logger_node

Registra la misión.

Genera archivos en:

```text
reports/mission_logs/
```

---

## 7. Archivos generados

Después de ejecutar la demo completa, se generan archivos como:

```text
reports/mission_logs/ros_mission_YYYYMMDD_HHMMSS.csv
reports/mission_logs/ros_mission_YYYYMMDD_HHMMSS.jsonl
reports/mission_logs/mission_route_YYYYMMDD_HHMMSS.png
```

También se pueden generar reportes en:

```text
reports/mission_reports/
```

---

## 8. Generar reporte de misión

Después de ejecutar una misión:

```bash
python3 scripts/generate_mission_report.py
```

Con un CSV específico:

```bash
python3 scripts/generate_mission_report.py reports/mission_logs/ros_mission_YYYYMMDD_HHMMSS.csv
```

---

## 9. Generar visualización 2D

Después de ejecutar una misión:

```bash
python3 scripts/visualize_mission_route.py
```

Con un CSV específico:

```bash
python3 scripts/visualize_mission_route.py reports/mission_logs/ros_mission_YYYYMMDD_HHMMSS.csv
```

---

## 10. Ejecutar dashboard

Con el entorno virtual activado:

```bash
streamlit run app/streamlit_rescuetwin_dashboard.py
```

El dashboard muestra la última misión registrada, sensores, riesgo, alertas, ruta y bitácora.

---

## 11. Ejecutar tests

Desde la raíz del proyecto:

```bash
pytest tests
```

Resultado esperado:

```text
17 passed
```

---

## 12. Inspeccionar ROS manualmente

Si ejecutaste el proyecto con:

```bash
python3 run_rescuetwin_full_project.py --no-stop
```

podés entrar al contenedor:

```bash
docker exec -it rescuetwin_ros bash
```

Cargar ROS:

```bash
set +u
source /opt/ros/humble/setup.bash
cd /workspace/RescueTwin-AI/ros2_ws
source install/setup.bash
```

Ver topics:

```bash
ros2 topic list
```

Consultar algunos topics:

```bash
ros2 topic echo /robot/status --once
ros2 topic echo /robot/sensor_status --once
ros2 topic echo /robot/risk_status --once
ros2 topic echo /mission/state --once
ros2 topic echo /mission/decision_status --once
ros2 topic echo /base/alertas --once
```

---

## 13. Ejecutar notebooks

Los notebooks se ejecutan en este orden:

```text
1. notebooks/01_exploracion_fuentes.ipynb
2. notebooks/02_eda_rescuetwin.ipynb
3. notebooks/03_modelado_rescuetwin.ipynb
```

El primer notebook genera el dataset procesado.

El segundo notebook genera gráficos del EDA.

El tercero entrena y exporta el modelo IA.

---

## 14. Archivos principales

```text
run_rescuetwin_full_project.py
app/streamlit_rescuetwin_dashboard.py
scripts/generate_mission_report.py
scripts/visualize_mission_route.py
data/processed/rescuetwin_dataset.csv
models/random_forest_rescuetwin.pkl
models/model_columns.pkl
```

---

## 15. Problemas frecuentes

### Docker no responde

Abrir Docker Desktop y ejecutar:

```bash
docker ps
```

---

### ROS no encuentra el paquete

Dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
rm -rf build install log
colcon build
source install/setup.bash
```

---

### Error al cargar el modelo IA

Dentro del contenedor:

```bash
pip3 uninstall -y numpy scipy scikit-learn pandas joblib

pip3 install --no-cache-dir \
  numpy==2.2.6 \
  scipy==1.15.3 \
  scikit-learn==1.7.2 \
  pandas==2.3.3 \
  joblib==1.5.3
```

---

### Gazebo no abre visualmente en Mac

Usar modo headless:

```bash
gzserver ros2_ws/src/rescuetwin_sim/worlds/collapse_world.world --verbose
```

---

### El reporte falla por tabulate

```bash
pip install tabulate
```

---

### El visualizador no encuentra CSV

Primero ejecutar:

```bash
python3 run_rescuetwin_full_project.py
```

Después:

```bash
python3 scripts/visualize_mission_route.py
```
