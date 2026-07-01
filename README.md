# RescueTwin AI

## Gemelo digital de un robot cuadrúpedo para rescate en derrumbes

RescueTwin AI es un proyecto de Ciencia de Datos que propone el desarrollo de un gemelo digital para un robot cuadrúpedo utilizado en operaciones de rescate urbano, especialmente en zonas de derrumbe.

El sistema utiliza datos de sensores ambientales, químicos, estructurales y operativos para predecir el nivel de riesgo de una zona y recomendar una acción operativa para el robot.

La versión final del proyecto se enfoca en el siguiente flujo:

```text
Notebooks → Dataset → Modelo predictivo → Agente autónomo → Streamlit → Unity 3D
```

---

# 1. Objetivo del proyecto

El objetivo principal es construir un modelo predictivo capaz de clasificar el nivel de riesgo operativo de una zona de derrumbe a partir de datos de sensores simulados e integrados desde distintas fuentes públicas.

La salida del sistema permite indicar si el robot debe:

- Avanzar.
- Avanzar con precaución.
- Cambiar de ruta.
- Detenerse.
- Enviar una alerta al equipo de rescate.

---

# 2. Problemática

En situaciones de derrumbe, enviar personal humano a inspeccionar una zona puede representar un riesgo elevado. Pueden existir obstáculos, vibraciones estructurales, gases peligrosos, baja visibilidad, falta de comunicación o posibles nuevos colapsos.

Un robot cuadrúpedo puede ingresar primero, recolectar datos del entorno y enviar información al equipo de rescate. A partir de esos datos, el gemelo digital permite tomar decisiones más seguras y basadas en información.

---

# 3. Hipótesis

A partir de datos de sensores ambientales, estructurales y operativos de un robot cuadrúpedo, es posible predecir el nivel de riesgo de una zona de derrumbe y recomendar acciones que reduzcan la exposición del personal de rescate.

---

# 4. Dominio del negocio

El proyecto se ubica dentro del dominio de:

**Robótica aplicada a emergencias, rescate urbano y seguridad operativa.**

Posibles usuarios o clientes:

- Bomberos.
- Defensa Civil.
- Equipos de búsqueda y rescate.
- Municipios.
- Empresas industriales.
- Mineras.
- Organismos de respuesta ante catástrofes.

---

# 5. Propuesta de valor

RescueTwin AI aporta valor porque permite:

- Reducir la exposición humana en zonas peligrosas.
- Tomar decisiones basadas en datos.
- Priorizar zonas de búsqueda.
- Detectar condiciones ambientales o estructurales críticas.
- Estimar si el robot puede continuar operando.
- Recomendar acciones operativas.
- Visualizar la misión en 3D para facilitar la interpretación técnica y de negocio.

---

# 6. Fuentes de datos utilizadas

No existe un único dataset público que represente completamente a un robot cuadrúpedo operando dentro de una zona de derrumbe. Por ese motivo, se construyó un dataset integrado a partir de varias fuentes públicas y variables simuladas coherentes con el caso de uso.

| Fuente                         | Tipo de dato                   | Uso dentro del proyecto                                                |
| ------------------------------ | ------------------------------ | ---------------------------------------------------------------------- |
| Indoor Environmental Dataset   | Sensores ambientales           | Temperatura, humedad, presión, luz, sonido, CO2 y partículas           |
| UCI Gas Sensor Dataset         | Sensores químicos              | Tipo de gas y concentración estimada                                   |
| NASA Battery Dataset Cleaned   | Datos de batería               | Batería restante, voltaje, temperatura de batería y autonomía estimada |
| SARD Search and Rescue Dataset | Imágenes de búsqueda y rescate | Referencia para simular detección de personas atrapadas                |

---

# 7. Dataset final

El dataset final generado se encuentra en:

```text
data/processed/rescuetwin_dataset.csv
```

Este dataset integra variables ambientales, químicas, estructurales y operativas del robot.

Variables principales:

```text
temperatura
humedad
presion
luz
sonido_db
co2
particulas_pm25
gas_tipo
gas_ppm
vibracion
inclinacion
distancia_obstaculo
velocidad_robot
senal_comunicacion
bateria
voltaje_bateria
temperatura_bateria
autonomia_estimada_min
visibilidad
persona_detectada
confianza_persona
nivel_riesgo
accion_recomendada
```

---

# 8. Estructura del proyecto

```text
RescueTwin-AI/
├── app/
│   ├── autonomous/
│   └── streamlit_rescuetwin_dashboard.py
├── config/
├── data/
│   └── processed/
│       └── rescuetwin_dataset.csv
├── models/
│   ├── random_forest_rescuetwin.pkl
│   ├── model_columns.pkl
│   └── autonomous/
├── notebooks/
│   ├── 01_exploracion_fuentes.ipynb
│   ├── 02_eda_rescuetwin.ipynb
│   └── 03_modelado_rescuetwin.ipynb
├── reports/
│   ├── graficos/
│   ├── metrics/
│   └── mission_logs/
├── scripts/
│   ├── run_autonomous_learning_mission.py
│   ├── export_mission_to_unity.py
│   ├── generate_mission_report.py
│   ├── visualize_mission_route.py
│   ├── visualize_autonomous_mission.py
│   └── analyze_autonomous_results.py
├── tests/
├── unity/
│   └── RescueTwinUnity_v2/
├── README.md
├── requirements.txt
└── pytest.ini
```

---

# 9. Componentes principales

## 9.1 Notebooks

Los notebooks representan la parte central de Ciencia de Datos.

```text
notebooks/01_exploracion_fuentes.ipynb
```

Explora e integra las fuentes de datos.

```text
notebooks/02_eda_rescuetwin.ipynb
```

Realiza el análisis exploratorio de datos.

```text
notebooks/03_modelado_rescuetwin.ipynb
```

Entrena y evalúa el modelo predictivo.

---

## 9.2 Modelo predictivo

El modelo entrenado se encuentra en:

```text
models/random_forest_rescuetwin.pkl
```

Las columnas esperadas por el modelo se encuentran en:

```text
models/model_columns.pkl
```

El modelo clasifica el nivel de riesgo operativo:

```text
Bajo
Medio
Alto
```

Luego, a partir del riesgo y el contexto de misión, el sistema recomienda una acción.

---

## 9.3 Agente autónomo

La lógica autónoma se encuentra en:

```text
app/autonomous/
```

Archivos principales:

```text
actions.py
experience_memory.py
mission_runner.py
procedural_world.py
q_learning_agent.py
reward_function.py
sensor_fusion.py
state.py
```

El agente autónomo permite generar misiones simuladas sin depender de una entrada manual de sensores. Esto hace que el flujo sea más realista, ya que el operador no controla directamente la temperatura, el gas o la vibración, sino que observa los datos generados durante la misión.

---

## 9.4 Control anti-bucles del agente

Se incorporó una mejora para evitar comportamientos repetitivos del robot.

Problemas detectados:

```text
AVANZAR
AVANZAR
AVANZAR
```

contra un obstáculo, o:

```text
ESCANEAR
ESCANEAR
ESCANEAR
```

sin obtener nueva información.

Solución aplicada:

- Penalización por repetición y estancamiento.
- Bloqueo temporal de acciones inútiles.
- Registro de acciones bloqueadas.
- Mejora en la toma de decisiones del agente.

Archivos relacionados:

```text
app/autonomous/q_learning_agent.py
app/autonomous/reward_function.py
app/autonomous/experience_memory.py
app/autonomous/mission_runner.py
tests/test_autonomous_agent.py
```

---

## 9.5 Streamlit

El dashboard principal es:

```text
app/streamlit_rescuetwin_dashboard.py
```

Este dashboard permite mostrar:

- Dominio del negocio.
- Hipótesis.
- Fuentes de datos.
- Dataset final.
- EDA.
- Misión simulada.
- Ruta 2D.
- Evolución de sensores.
- Riesgo y acciones recomendadas.
- Archivos usados por Unity.

Streamlit no modifica manualmente las condiciones del entorno. Su función es mostrar los datos analizados y la misión generada por el sistema.

---

## 9.6 Unity 3D

La visualización 3D se encuentra en:

```text
unity/RescueTwinUnity_v2/
```

Unity lee archivos JSON exportados desde Python:

```text
unity/RescueTwinUnity_v2/Assets/StreamingAssets/custom_mission_XXX_trajectory.json
unity/RescueTwinUnity_v2/Assets/StreamingAssets/custom_mission_XXX_world.json
```

La trayectoria y el mundo no se definen manualmente dentro de Unity. Unity funciona como visualizador 3D de una misión generada previamente por el agente autónomo.

---

# 10. Requisitos previos

Tener instalado:

- Python 3.10
- Git
- Unity Hub
- Unity Editor
- VS Code o editor similar

---

# 11. Instalación desde cero

Clonar el repositorio:

```bash
cd ~/Downloads
git clone https://github.com/Nicom7910/RescueTwin-AI.git
cd RescueTwin-AI
```

Crear entorno virtual:

```bash
python3.10 -m venv venv
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verificar instalación:

```bash
python -c "import pandas; print('pandas OK')"
python -c "import sklearn; print('sklearn OK')"
python -c "import streamlit; print('streamlit OK')"
python -c "import plotly.express as px; print('plotly OK')"
```

---

# 12. Ejecutar notebooks

Activar entorno:

```bash
source venv/bin/activate
```

Levantar Jupyter:

```bash
jupyter notebook
```

Ejecutar los notebooks en este orden:

```text
1. notebooks/01_exploracion_fuentes.ipynb
2. notebooks/02_eda_rescuetwin.ipynb
3. notebooks/03_modelado_rescuetwin.ipynb
```

El objetivo de los notebooks es mostrar:

- Construcción e integración de datos.
- Análisis exploratorio.
- Entrenamiento y evaluación del modelo.

---

# 13. Ejecutar dashboard Streamlit

Con el entorno virtual activado:

```bash
streamlit run app/streamlit_rescuetwin_dashboard.py
```

Abrir en el navegador:

```text
http://localhost:8501
```

Secciones principales:

```text
Dominio e hipótesis
Fuentes y dataset
EDA
Misión simulada
Unity 3D
```

---

# 14. Crear nuevas misiones autónomas

Para generar nuevas misiones:

```bash
python3 scripts/run_autonomous_learning_mission.py --episodes 10 --max-steps 80
```

Para generar más misiones:

```bash
python3 scripts/run_autonomous_learning_mission.py --episodes 50 --max-steps 120
```

Las misiones se generan en:

```text
reports/autonomous_missions/
```

---

# 15. Entrenar nuevamente el agente

Si se modificó la lógica de recompensa o se quiere reentrenar desde cero, se recomienda apartar la Q-table anterior:

```bash
mv models/autonomous/q_table.json models/autonomous/q_table_v1_backup.json
```

Luego ejecutar:

```bash
python3 scripts/run_autonomous_learning_mission.py --episodes 100 --max-steps 120
```

Evaluar sin aprendizaje:

```bash
python3 scripts/run_autonomous_learning_mission.py --episodes 10 --max-steps 120 --eval
```

---

# 16. Exportar una misión a Unity

Para exportar una misión específica a Unity:

```bash
python3 scripts/export_mission_to_unity.py NUMERO_DE_MISION
```

Ejemplo:

```bash
python3 scripts/export_mission_to_unity.py 5
```

Esto genera archivos como:

```text
unity/RescueTwinUnity_v2/Assets/StreamingAssets/custom_mission_005_trajectory.json
unity/RescueTwinUnity_v2/Assets/StreamingAssets/custom_mission_005_world.json
```

También genera un reporte de la misión exportada.

---

# 17. Flujo recomendado para demo

Ejecutar desde la raíz del proyecto:

```bash
source venv/bin/activate

python3 scripts/run_autonomous_learning_mission.py --episodes 10 --max-steps 80

python3 scripts/export_mission_to_unity.py 5

streamlit run app/streamlit_rescuetwin_dashboard.py
```

Importante: `streamlit run` deja la terminal ocupada. Si se quiere ejecutar otros comandos al mismo tiempo, abrir otra terminal.

---

# 18. Configurar Unity

Abrir Unity Hub.

Seleccionar:

```text
Open → Add project from disk
```

Elegir la carpeta:

```text
RescueTwin-AI/unity/RescueTwinUnity_v2
```

En la escena principal, configurar:

```text
MissionReplayController
Mission File Name = custom_mission_005_trajectory.json
Use Demo Selector = false
```

Configurar:

```text
MissionMapBuilder
World File Name = custom_mission_005_world.json
Trajectory File Name = custom_mission_005_trajectory.json
```

Presionar:

```text
Play
```

Unity reproducirá la misión exportada.

---

# 19. Ejecutar tests

Desde la raíz del proyecto:

```bash
pytest
```

---

# 20. Scripts principales

## scripts/run_autonomous_learning_mission.py

Genera misiones autónomas usando el agente de aprendizaje.

Ejemplo:

```bash
python3 scripts/run_autonomous_learning_mission.py --episodes 10 --max-steps 80
```

---

## scripts/export_mission_to_unity.py

Exporta una misión generada hacia Unity.

Ejemplo:

```bash
python3 scripts/export_mission_to_unity.py 5
```

---

## scripts/generate_mission_report.py

Genera reportes de misión.

Ejemplo:

```bash
python3 scripts/generate_mission_report.py
```

---

## scripts/visualize_autonomous_mission.py

Permite visualizar una misión autónoma generada.

Ejemplo:

```bash
python3 scripts/visualize_autonomous_mission.py
```

---

## scripts/analyze_autonomous_results.py

Analiza resultados del agente autónomo.

Ejemplo:

```bash
python3 scripts/analyze_autonomous_results.py
```

---

# 21. Archivos que no deben subirse

El proyecto ignora automáticamente:

```text
venv/
__pycache__/
.pytest_cache/
.ipynb_checkpoints/
data/raw/
reports/autonomous_missions/
reports/unity_demo_scenarios/
unity/**/Library/
unity/**/Temp/
unity/**/Logs/
unity/**/UserSettings/
```

También se recomienda no subir grandes cantidades de misiones generadas automáticamente. Para la entrega, mantener solo una misión demo final en Unity, por ejemplo:

```text
custom_mission_005_trajectory.json
custom_mission_005_world.json
```

---

# 22. Flujo conceptual para presentar

```text
1. Se integran fuentes de datos públicas y variables simuladas.
2. Se construye un dataset final.
3. Se realiza EDA para comprender los factores de riesgo.
4. Se entrena un modelo predictivo.
5. El agente autónomo genera una misión simulada.
6. Streamlit muestra datos, EDA, sensores, ruta y riesgo.
7. Unity visualiza en 3D el mundo y la trayectoria.
```

Frase recomendada para la exposición:

```text
Python realiza el análisis y la generación de la misión.
Streamlit permite explicar y monitorear los datos.
Unity transforma esa misión en una visualización 3D comprensible para la toma de decisiones.
```

---

# 23. Problemas frecuentes

## Streamlit no encuentra Plotly

Instalar:

```bash
pip install plotly
```

o reinstalar dependencias:

```bash
pip install -r requirements.txt
```

---

## Streamlit no detecta la misión

Primero generar misiones:

```bash
python3 scripts/run_autonomous_learning_mission.py --episodes 10 --max-steps 80
```

Luego exportar una:

```bash
python3 scripts/export_mission_to_unity.py 5
```

Reiniciar Streamlit.

---

## Unity no carga la misión

Verificar que existan los archivos:

```text
unity/RescueTwinUnity_v2/Assets/StreamingAssets/custom_mission_005_trajectory.json
unity/RescueTwinUnity_v2/Assets/StreamingAssets/custom_mission_005_world.json
```

Verificar en Unity:

```text
MissionReplayController → Mission File Name
MissionMapBuilder → World File Name
```

---

## Unity sigue cargando demo_001

Desactivar:

```text
Use Demo Selector = false
```

Y configurar manualmente:

```text
custom_mission_005_trajectory.json
custom_mission_005_world.json
```

---

## Pytest falla por archivos eliminados

Actualizar los tests para que validen el flujo actual del proyecto.

El flujo actual ya no depende de ROS 2 ni Docker.

---

# 24. Estado final del proyecto

La versión final del proyecto queda enfocada en:

```text
Ciencia de Datos + Agente autónomo Python + Streamlit + Unity 3D
```
