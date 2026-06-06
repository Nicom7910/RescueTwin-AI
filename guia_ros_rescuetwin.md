# Guía de ejecución ROS/Gazebo - RescueTwin AI

Esta guía explica cómo levantar el contenedor Docker, cargar ROS 2 Humble, ejecutar el nodo de movimiento del robot y enviar comandos para simular su desplazamiento.

---

## 1. Abrir Docker Desktop

Antes de ejecutar comandos, abrir **Docker Desktop** en Mac y esperar a que quede corriendo.

```bash
docker ps
```

Si no tira error, Docker está funcionando.

---

## 2. Ir a la carpeta del proyecto

En la terminal de Mac:

```bash
cd /Users/nicom7910/Downloads/RescueTwin-AI
ls
```

Deberías ver carpetas como:

```text
app  data  models  notebooks  reports  ros2_ws
```

---

## 3. Levantar el contenedor

### Si el contenedor ya existe

```bash
docker start rescuetwin_ros
docker exec -it rescuetwin_ros bash
```

### Si el contenedor no existe

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

---

## 4. Cargar ROS dentro del contenedor

Una vez dentro del contenedor:

```bash
set +u
source /opt/ros/humble/setup.bash
cd /workspace/RescueTwin-AI/ros2_ws
source install/setup.bash
```

Verificar que el paquete esté disponible:

```bash
ros2 pkg list | grep rescuetwin_sim
```

Resultado esperado:

```text
rescuetwin_sim
```

Si no aparece, recompilar:

```bash
cd /workspace/RescueTwin-AI/ros2_ws
rm -rf build install log
colcon build
source install/setup.bash
ros2 pkg list | grep rescuetwin_sim
```

---

## 5. Validar el mundo Gazebo en modo servidor

Como Gazebo visual puede fallar en Mac + Docker por OpenGL, se valida el mundo en modo headless con `gzserver`:

```bash
cd /workspace/RescueTwin-AI
set +u
source /opt/ros/humble/setup.bash
gzserver ros2_ws/src/rescuetwin_sim/worlds/collapse_world.world --verbose
```

Si aparece una línea similar a:

```text
Loading world file [.../collapse_world.world]
Connected to gazebo master
```

el mundo está cargando correctamente.

Para detenerlo:

```text
CTRL + C
```

---

## 6. Ejecutar el nodo de movimiento del robot

En la primera terminal dentro del contenedor:

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

Esta terminal debe quedar abierta. Es el nodo que simula la posición del robot.

---

## 7. Abrir una segunda terminal para enviar comandos

En otra terminal de Mac:

```bash
docker exec -it rescuetwin_ros bash
```

Dentro del contenedor:

```bash
set +u
source /opt/ros/humble/setup.bash
cd /workspace/RescueTwin-AI/ros2_ws
source install/setup.bash
```

Verificar topics disponibles:

```bash
ros2 topic list
```

Deberías ver:

```text
/robot/cmd_vel
/robot/pose
/robot/status
```

---

## 8. Comandos para mover el robot

### Avanzar

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

### Avanzar más lento

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

### Girar sobre su eje

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.5}}"
```

### Avanzar girando

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.5}}"
```

### Retroceder

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.3}, angular: {z: 0.0}}"
```

### Detener el robot

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

---

## 9. Ver estado del robot

Para ver el estado una sola vez:

```bash
ros2 topic echo /robot/status --once
```

Ejemplo de salida:

```text
data: Robot simulado | x=15.65, y=0.49, theta=4.45, v=0.00, w=0.00
```

Significado:

| Campo | Significado |
|---|---|
| x | Posición horizontal simulada |
| y | Posición vertical simulada |
| theta | Orientación del robot |
| v | Velocidad lineal |
| w | Velocidad angular |

---

## 10. Ver pose del robot

Para ver la pose una sola vez:

```bash
ros2 topic echo /robot/pose --once
```

Esto muestra la posición del robot en formato `nav_msgs/Odometry`.

Campos principales:

```text
pose.pose.position.x
pose.pose.position.y
pose.pose.position.z
```

---

## 11. Evitar mensajes infinitos

Si usás:

```bash
ros2 topic echo /robot/status
```

ROS imprime mensajes continuamente hasta que lo cortes con:

```text
CTRL + C
```

Para ver solo un mensaje, usar:

```bash
ros2 topic echo /robot/status --once
```

Lo mismo aplica para `/robot/pose`.

---

## 12. Ejemplo completo de prueba

### Terminal 1

```bash
cd /Users/nicom7910/Downloads/RescueTwin-AI
docker start rescuetwin_ros
docker exec -it rescuetwin_ros bash
set +u
source /opt/ros/humble/setup.bash
cd /workspace/RescueTwin-AI/ros2_ws
source install/setup.bash
ros2 run rescuetwin_sim motion_node
```

### Terminal 2

```bash
docker exec -it rescuetwin_ros bash
set +u
source /opt/ros/humble/setup.bash
cd /workspace/RescueTwin-AI/ros2_ws
source install/setup.bash
```

Enviar avance:

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

Ver estado:

```bash
ros2 topic echo /robot/status --once
```

Enviar giro:

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.5}}"
```

Ver pose:

```bash
ros2 topic echo /robot/pose --once
```

Detener:

```bash
ros2 topic pub --once /robot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

Confirmar detención:

```bash
ros2 topic echo /robot/status --once
```

---

## 13. Interpretación para el proyecto

Esta ejecución representa la **Etapa 2 del simulador ROS/Gazebo**.

Aunque Gazebo visual no renderice correctamente en Docker sobre Mac, el movimiento del robot se valida por datos ROS:

```text
Comando de velocidad → Nodo de movimiento → Pose simulada → Estado del robot
```

Esto permite demostrar que el robot simulado responde a comandos y actualiza su posición dentro del sistema ROS.

En etapas posteriores, esta pose será utilizada para simular sensores ambientales y conectar el modelo de inteligencia artificial de riesgo.

---

## 14. Próxima etapa

La siguiente etapa del proyecto será crear un nodo de sensores simulados que publique topics como:

```text
/robot/temperatura
/robot/gas_ppm
/robot/vibracion
/robot/inclinacion
/robot/bateria
/robot/distancia_obstaculo
/robot/persona_detectada
```

Luego, el nodo IA usará esos sensores y el modelo `random_forest_rescuetwin.pkl` para publicar:

```text
/robot/nivel_riesgo
/robot/accion_recomendada
```
