# Guía completa de ejecución ROS/Gazebo - RescueTwin AI

Esta guía explica cómo levantar desde cero la extensión ROS/Gazebo del proyecto **RescueTwin AI**, cómo iniciar los nodos del robot, cómo moverlo, cómo consultar sensores simulados y cómo ejecutar el nodo de Inteligencia Artificial que predice el nivel de riesgo.

El flujo completo del sistema es:

```text
Comando de movimiento
        ↓
motion_node
        ↓
/robot/pose y /robot/status
        ↓
sensor_sim_node
        ↓
Sensores simulados
        ↓
risk_ai_node
        ↓
Nivel de riesgo + acción recomendada
```

---

## 1. Requisitos previos

Antes de empezar, asegurarse de tener:

- Docker Desktop abierto y funcionando.
- El proyecto en la carpeta local:

```text
/RescueTwin-AI
```

- La imagen Docker creada:

```text
rescuetwin_ros_image
```

- El contenedor llamado:

```text
rescuetwin_ros
```

- El modelo IA entrenado en:

```text
models/random_forest_rescuetwin.pkl
models/model_columns.pkl
```

---

## 2. Abrir Docker Desktop

En Mac, abrir **Docker Desktop** y esperar a que diga que está corriendo.

Luego, en una terminal de Mac:

```bash
docker ps
```

Si no muestra error, Docker está funcionando.

---

## 3. Ir a la carpeta del proyecto

Desde la terminal de Mac:

```bash
cd RescueTwin-AI
ls
```

Deberías ver algo similar a:

```text
README.md  app  data  models  notebooks  reports  requirements.txt  ros2_ws
```

---

## 4. Levantar el contenedor

### Caso A: el contenedor ya existe

```bash
docker start rescuetwin_ros
docker exec -it rescuetwin_ros bash
```

### Caso B: el contenedor no existe

Ejecutar desde la carpeta raíz del proyecto:

```bash
docker run -it \
  --name rescuetwin_ros \
  -e DISPLAY=host.docker.internal:0 \
  -e SDL_AUDIODRIVER=dummy \
  -e QT_X11_NO_MITSHM=1 \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -v "$(pwd)":/workspace/RescueTwin-AI \
  rescuetwin_ros_image \
  bash
```

Este comando monta el proyecto dentro del contenedor en:

```text
/workspace/RescueTwin-AI
```

---

## 5. Cargar ROS dentro del contenedor

Una vez dentro del contenedor, ejecutar siempre:

```bash
set +u
source /opt/ros/humble/setup.bash
cd /workspace/RescueTwin-AI/ros2_ws
source install/setup.bash
```

Verificar que el paquete del proyecto esté disponible:

```bash
ros2 pkg list | grep rescuetwin_sim
```

Resultado esperado:

```text
rescuetwin_sim
```

---

## 6. Recompilar el workspace si hace falta

Si agregaste o modificaste nodos, o si `ros2 pkg list` no encuentra el paquete, recompilar:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
rm -rf build install log
colcon build
source install/setup.bash
```

---

## 7. Validar el mundo Gazebo

En Mac + Docker, Gazebo visual puede fallar por OpenGL. Por eso se valida el mundo con `gzserver` en modo headless.

Desde dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI
set +u
source /opt/ros/humble/setup.bash
gzserver ros2_ws/src/rescuetwin_sim/worlds/collapse_world.world --verbose
```

Si aparece algo parecido a:

```text
Loading world file [.../collapse_world.world]
Connected to gazebo master
```

significa que el mundo Gazebo de derrumbe carga correctamente.

Para detenerlo:

```text
CTRL + C
```

---

## 8. Verificar versiones de Python para el nodo IA

El modelo fue entrenado con versiones nuevas de NumPy y scikit-learn. Dentro del contenedor, verificar:

```bash
python3 -c "import numpy, scipy, sklearn, pandas, joblib; print('numpy', numpy.__version__); print('scipy', scipy.__version__); print('sklearn', sklearn.__version__); print('pandas', pandas.__version__); print('joblib', joblib.__version__)"
```

Versiones esperadas:

```text
numpy 2.2.6
scipy 1.15.3
sklearn 1.7.2
pandas 2.3.3
joblib 1.5.3
```

Si no coinciden o aparece error al cargar el modelo, reinstalar:

```bash
pip3 uninstall -y numpy scipy scikit-learn pandas joblib

pip3 install --no-cache-dir \
  numpy==2.2.6 \
  scipy==1.15.3 \
  scikit-learn==1.7.2 \
  pandas==2.3.3 \
  joblib==1.5.3
```

Probar que el modelo carga:

```bash
cd /workspace/RescueTwin-AI
python3 -c "import joblib; modelo = joblib.load('models/random_forest_rescuetwin.pkl'); columnas = joblib.load('models/model_columns.pkl'); print('Modelo cargado OK'); print(type(modelo)); print(len(columnas))"
```

Resultado esperado:

```text
Modelo cargado OK
```

---

# Ejecución completa del proyecto ROS

Para ejecutar todo el sistema se usan 4 terminales.

---

## Terminal 1: nodo de movimiento

Desde una terminal de Mac:

```bash
cd RescueTwin-AI
docker start rescuetwin_ros
docker exec -it rescuetwin_ros bash
```

Dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run rescuetwin_sim motion_node
```

Resultado esperado:

```text
Motion Node iniciado. Esperando comandos en /robot/cmd_vel
```

Este nodo publica:

```text
/robot/pose
/robot/status
```

---

## Terminal 2: nodo de sensores simulados

Abrir otra terminal de Mac:

```bash
docker exec -it rescuetwin_ros bash
```

Dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run rescuetwin_sim sensor_sim_node
```

Resultado esperado:

```text
Sensor Sim Node iniciado. Publicando sensores simulados del robot.
```

Este nodo lee:

```text
/robot/pose
```

Y publica:

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

---

## Terminal 3: nodo IA de riesgo

Abrir otra terminal de Mac:

```bash
docker exec -it rescuetwin_ros bash
```

Dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run rescuetwin_sim risk_ai_node
```

Resultado esperado:

```text
Modelo cargado desde: /workspace/RescueTwin-AI/models/random_forest_rescuetwin.pkl
Risk AI Node iniciado. Modelo IA cargado correctamente.
```

Este nodo lee sensores y publica:

```text
/robot/nivel_riesgo
/robot/accion_recomendada
/robot/risk_status
```

---

## Terminal 4: control y consulta

Abrir otra terminal de Mac:

```bash
docker exec -it rescuetwin_ros bash
```

Dentro del contenedor:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Ver todos los topics activos:

```bash
ros2 topic list
```

Deberían aparecer, entre otros:

```text
/robot/cmd_vel
/robot/pose
/robot/status
/robot/temperatura
/robot/gas_ppm
/robot/vibracion
/robot/inclinacion
/robot/bateria
/robot/distancia_obstaculo
/robot/persona_detectada
/robot/sensor_status
/robot/nivel_riesgo
/robot/accion_recomendada
/robot/risk_status
```

---

# Comandos para mover el robot

## Avanzar

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

## Avanzar más rápido

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.8}, angular: {z: 0.0}}"
```

## Girar mientras avanza

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.5}}"
```

## Girar en sentido contrario

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: -0.5}}"
```

## Detener el robot

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

---

# Consultar estado del robot

## Ver estado de movimiento una sola vez

```bash
ros2 topic echo /robot/status --once
```

Ejemplo esperado:

```text
data: Robot simulado | x=2.15, y=0.40, theta=0.50, v=0.50, w=0.00
```

## Ver pose completa una sola vez

```bash
ros2 topic echo /robot/pose --once
```

La pose muestra la posición `x`, `y`, `z` del robot.

---

# Consultar sensores simulados

## Ver resumen de sensores una sola vez

```bash
ros2 topic echo /robot/sensor_status --once
```

Ejemplo esperado:

```text
data: Sensores | x=2.10, y=0.30, temp=26.4C, gas=65.2ppm, vib=0.30, inc=5.1deg, bateria=98.8%, obstaculo=4.30m, persona=0
```

## Ver sensores individuales

```bash
ros2 topic echo /robot/temperatura --once
ros2 topic echo /robot/gas_ppm --once
ros2 topic echo /robot/vibracion --once
ros2 topic echo /robot/inclinacion --once
ros2 topic echo /robot/bateria --once
ros2 topic echo /robot/distancia_obstaculo --once
ros2 topic echo /robot/persona_detectada --once
```

---

# Consultar IA de riesgo

## Ver resultado IA una sola vez

```bash
ros2 topic echo /robot/risk_status --once
```

Ejemplo esperado:

```text
data: Riesgo IA | nivel=Medio | accion=Avanzar con precaucion | temp=28.1C | gas=120.5ppm | vib=0.60 | inc=8.5deg | bateria=96.4% | obstaculo=3.40m | persona=0
```

## Ver nivel de riesgo solamente

```bash
ros2 topic echo /robot/nivel_riesgo --once
```

Ejemplo:

```text
data: Medio
```

## Ver acción recomendada solamente

```bash
ros2 topic echo /robot/accion_recomendada --once
```

Ejemplo:

```text
data: Avanzar con precaucion
```

---

# Ejemplo completo de prueba

Con las 3 primeras terminales corriendo `motion_node`, `sensor_sim_node` y `risk_ai_node`, en la Terminal 4 ejecutar:

```bash
ros2 topic echo /robot/status --once
ros2 topic echo /robot/sensor_status --once
ros2 topic echo /robot/risk_status --once
```

Mover el robot hacia adelante:

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.8}, angular: {z: 0.0}}"
```

Esperar 3 segundos.

Detener:

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

Consultar nuevamente:

```bash
ros2 topic echo /robot/status --once
ros2 topic echo /robot/sensor_status --once
ros2 topic echo /robot/risk_status --once
```

Interpretación:

- Si `x` o `y` cambiaron, el robot se movió.
- Si cambian gas, vibración, temperatura o inclinación, los sensores están respondiendo al entorno.
- Si cambia `nivel`, la IA está clasificando el riesgo según los sensores.

---

# Por qué a veces imprime muchas líneas

Los comandos:

```bash
ros2 topic echo /robot/status
ros2 topic echo /robot/pose
ros2 topic echo /robot/sensor_status
ros2 topic echo /robot/risk_status
```

sin `--once` quedan escuchando en tiempo real y muestran mensajes continuamente.

Para evitar el “choclo”, usar siempre:

```bash
--once
```

Ejemplo:

```bash
ros2 topic echo /robot/risk_status --once
```

Para cortar un comando que imprime sin parar:

```text
CTRL + C
```

---

# Solución de errores frecuentes

## Error: Package 'rescuetwin_sim' not found

Cargar ROS y el workspace:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 pkg list | grep rescuetwin_sim
```

Si sigue sin aparecer:

```bash
rm -rf build install log
colcon build
source install/setup.bash
```

---

## Error: No module named rescuetwin_sim.sensor_sim_node o risk_ai_node

Verificar que el archivo exista en la carpeta correcta:

```bash
ls /workspace/RescueTwin-AI/ros2_ws/src/rescuetwin_sim/rescuetwin_sim
```

Deberías ver:

```text
__init__.py
motion_node.py
sensor_sim_node.py
risk_ai_node.py
```

Luego recompilar:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
rm -rf build install log
colcon build
source install/setup.bash
```

---

## Error de NumPy, SciPy o scikit-learn al correr risk_ai_node

Reinstalar versiones compatibles:

```bash
pip3 uninstall -y numpy scipy scikit-learn pandas joblib

pip3 install --no-cache-dir \
  numpy==2.2.6 \
  scipy==1.15.3 \
  scikit-learn==1.7.2 \
  pandas==2.3.3 \
  joblib==1.5.3
```

Probar modelo:

```bash
cd /workspace/RescueTwin-AI
python3 -c "import joblib; modelo = joblib.load('models/random_forest_rescuetwin.pkl'); columnas = joblib.load('models/model_columns.pkl'); print('Modelo cargado OK'); print(type(modelo)); print(len(columnas))"
```

---

## Gazebo abre xeyes pero no abre la escena 3D

En Mac + Docker + XQuartz puede fallar el renderizado OpenGL con errores como:

```text
Unable to create glx context
GLWidget could not create a scene
```

En ese caso, validar Gazebo sin interfaz gráfica:

```bash
gzserver ros2_ws/src/rescuetwin_sim/worlds/collapse_world.world --verbose
```

Para el TP, el circuito ROS puede ejecutarse correctamente aunque Gazebo GUI no renderice en Mac.

---

# Comandos de Git para guardar cambios

Después de completar una etapa:

```bash
cd RescueTwin-AI
git status
git add ros2_ws/src/rescuetwin_sim
git commit -m "Actualizar simulacion ROS de RescueTwin AI"
git push
```

Para la Etapa 4 específicamente:

```bash
git add ros2_ws/src/rescuetwin_sim/rescuetwin_sim/risk_ai_node.py
git add ros2_ws/src/rescuetwin_sim/setup.py
git commit -m "Agregar nodo ROS IA de prediccion de riesgo"
git push
```

---

# Resumen rápido

Ejecutar estos nodos en tres terminales separadas:

```bash
ros2 run rescuetwin_sim motion_node
```

```bash
ros2 run rescuetwin_sim sensor_sim_node
```

```bash
ros2 run rescuetwin_sim risk_ai_node
```

En una cuarta terminal:

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.8}, angular: {z: 0.0}}"
ros2 topic echo /robot/status --once
ros2 topic echo /robot/sensor_status --once
ros2 topic echo /robot/risk_status --once
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

Con eso queda levantado el flujo completo de RescueTwin AI en ROS:

```text
Movimiento → Sensores → IA → Riesgo + Acción recomendada
```
