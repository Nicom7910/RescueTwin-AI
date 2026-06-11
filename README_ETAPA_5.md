# Etapa 5 - RescueTwin AI

Esta etapa agrega realismo al sistema ROS:

## 5.1 Nodo de decisión autónoma

Archivo:

```text
ros2_ws/src/rescuetwin_sim/rescuetwin_sim/decision_node.py
```

El nodo lee:

```text
/robot/pose
/robot/sensor_status
/robot/risk_status
```

y publica:

```text
/robot/cmd_vel
/base/alertas
/mission/state
/mission/current_objective
/mission/decision_status
```

## 5.2 Alertas a la base

Las alertas salen por:

```text
/base/alertas
```

Ejemplo:

```text
ALERTA BASE #1 | estado=EVITANDO_RIESGO | x=4.25, y=2.10 | Riesgo alto/sensor crítico...
```

## 5.3 Bitácora de misión

Archivo:

```text
ros2_ws/src/rescuetwin_sim/rescuetwin_sim/mission_logger_node.py
```

Genera logs en:

```text
reports/mission_logs/
```

Formatos:

```text
ros_mission_YYYYMMDD_HHMMSS.csv
ros_mission_YYYYMMDD_HHMMSS.jsonl
```

## 5.4 Visualización 2D

Archivo:

```text
scripts/visualize_mission_route.py
```

Genera:

```text
reports/mission_logs/mission_route_YYYYMMDD_HHMMSS.png
```

## Modificación necesaria en setup.py

En:

```text
ros2_ws/src/rescuetwin_sim/setup.py
```

Agregar los entry points:

```python
entry_points={
    'console_scripts': [
        'motion_node = rescuetwin_sim.motion_node:main',
        'sensor_sim_node = rescuetwin_sim.sensor_sim_node:main',
        'risk_ai_node = rescuetwin_sim.risk_ai_node:main',
        'decision_node = rescuetwin_sim.decision_node:main',
        'mission_logger_node = rescuetwin_sim.mission_logger_node:main',
    ],
},
```

## Compilar

Dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
rm -rf build install log
colcon build
source install/setup.bash
```

## Ejecutar el sistema completo

Terminal 1:

```bash
ros2 run rescuetwin_sim motion_node
```

Terminal 2:

```bash
ros2 run rescuetwin_sim sensor_sim_node
```

Terminal 3:

```bash
ros2 run rescuetwin_sim risk_ai_node
```

Terminal 4:

```bash
ros2 run rescuetwin_sim decision_node
```

Terminal 5:

```bash
ros2 run rescuetwin_sim mission_logger_node
```

## Ver resultados

```bash
ros2 topic echo /mission/state --once
ros2 topic echo /mission/current_objective --once
ros2 topic echo /mission/decision_status --once
ros2 topic echo /base/alertas --once
ros2 topic echo /mission/log_status --once
```

## Visualizar ruta

Desde Mac, en la raíz del proyecto:

```bash
python3 scripts/visualize_mission_route.py
```

Si falta matplotlib:

```bash
pip install matplotlib pandas
```

## Commit sugerido

```bash
git add ros2_ws/src/rescuetwin_sim/rescuetwin_sim/decision_node.py
git add ros2_ws/src/rescuetwin_sim/rescuetwin_sim/mission_logger_node.py
git add scripts/visualize_mission_route.py
git add config/mission_map.json
git add ros2_ws/src/rescuetwin_sim/setup.py
git commit -m "Agregar decision autonoma alertas bitacora y visualizacion de mision"
git push
```
