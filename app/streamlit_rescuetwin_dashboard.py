from pathlib import Path
import json
import re

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ModuleNotFoundError:
    PLOTLY_AVAILABLE = False


# CONFIGURACIÓN GENERAL

ROOT = Path(__file__).resolve().parents[1]

DATASET_FILE = ROOT / "data" / "processed" / "rescuetwin_dataset.csv"

MISSION_LOGS_DIR = ROOT / "reports" / "mission_logs"

UNITY_STREAMING_ASSETS = (
    ROOT
    / "unity"
    / "RescueTwinUnity_v2"
    / "Assets"
    / "StreamingAssets"
)

st.set_page_config(
    page_title="RescueTwin AI Dashboard",
    layout="wide"
)


# FUNCIONES AUXILIARES

def safe_read_json(path: Path):
    if path is None or not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_latest_file(directory: Path, patterns):
    """
    Busca el archivo más reciente dentro de un directorio usando uno o varios patrones.
    """
    if not directory.exists():
        return None

    files = []

    for pattern in patterns:
        files.extend(directory.glob(pattern))

    files = [f for f in files if f.is_file()]

    if not files:
        return None

    return max(files, key=lambda p: p.stat().st_mtime)


def get_unity_missions():
    """
    Devuelve todas las misiones exportadas a Unity detectadas en StreamingAssets.
    """
    if not UNITY_STREAMING_ASSETS.exists():
        return []

    trajectory_files = sorted(
        UNITY_STREAMING_ASSETS.glob("*_trajectory.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return trajectory_files


def get_matching_world_file(trajectory_file: Path):
    """
    Dado custom_mission_018_trajectory.json intenta encontrar custom_mission_018_world.json.
    """
    if trajectory_file is None:
        return None

    world_name = trajectory_file.name.replace("_trajectory.json", "_world.json")
    world_file = trajectory_file.parent / world_name

    if world_file.exists():
        return world_file

    return None


def extract_mission_number(path: Path):
    if path is None:
        return None

    match = re.search(r"custom_mission_(\d+)_trajectory\.json", path.name)

    if match:
        return match.group(1)

    return None


def normalize_trajectory_json(data):
    """
    Soporta distintas estructuras posibles:
    - {"trajectory": [...]}
    - {"points": [...]}
    - {"mission": {"trajectory": [...]}}
    - [...]
    """
    if data is None:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if "trajectory" in data and isinstance(data["trajectory"], list):
            return data["trajectory"]

        if "points" in data and isinstance(data["points"], list):
            return data["points"]

        if "path" in data and isinstance(data["path"], list):
            return data["path"]

        if "mission" in data and isinstance(data["mission"], dict):
            mission = data["mission"]

            if "trajectory" in mission and isinstance(mission["trajectory"], list):
                return mission["trajectory"]

            if "points" in mission and isinstance(mission["points"], list):
                return mission["points"]

    return []


def load_dataset():
    if DATASET_FILE.exists():
        try:
            return pd.read_csv(DATASET_FILE)
        except Exception as e:
            st.error(f"No se pudo leer el dataset procesado: {e}")
            return None

    return None


def load_unity_trajectory(trajectory_file: Path):
    data = safe_read_json(trajectory_file)
    trajectory = normalize_trajectory_json(data)

    if not trajectory:
        return None

    df = pd.DataFrame(trajectory)

    # Normalización básica de nombres
    rename_map = {}

    if "pos_x" in df.columns and "x" not in df.columns:
        rename_map["pos_x"] = "x"

    if "pos_y" in df.columns and "y" not in df.columns:
        rename_map["pos_y"] = "y"

    if "pos_z" in df.columns and "z" not in df.columns:
        rename_map["pos_z"] = "z"

    if "risk" in df.columns and "riesgo" not in df.columns:
        rename_map["risk"] = "riesgo"

    if "risk_level" in df.columns and "riesgo" not in df.columns:
        rename_map["risk_level"] = "riesgo"

    if "action" in df.columns and "accion" not in df.columns:
        rename_map["action"] = "accion"

    if "battery" in df.columns and "bateria" not in df.columns:
        rename_map["battery"] = "bateria"

    if "gas" in df.columns and "gas_ppm" not in df.columns:
        rename_map["gas"] = "gas_ppm"

    if "temperature" in df.columns and "temperatura" not in df.columns:
        rename_map["temperature"] = "temperatura"

    if rename_map:
        df = df.rename(columns=rename_map)

    # Si no hay step, lo generamos
    if "step" not in df.columns:
        df["step"] = range(len(df))

    return df


def load_latest_ros_csv():
    csv_file = get_latest_file(
        MISSION_LOGS_DIR,
        ["ros_mission_*.csv"]
    )

    if csv_file is None:
        return None, None

    try:
        df = pd.read_csv(csv_file)
        return df, csv_file
    except Exception:
        return None, csv_file


def risk_label(value):
    text = str(value).lower()

    if "alto" in text or "high" in text:
        return "🔴 Alto"

    if "medio" in text or "medium" in text:
        return "🟡 Medio"

    if "bajo" in text or "low" in text:
        return "🟢 Bajo"

    return str(value)


def find_column(df, candidates):
    if df is None:
        return None

    columns_lower = {col.lower(): col for col in df.columns}

    for candidate in candidates:
        if candidate.lower() in columns_lower:
            return columns_lower[candidate.lower()]

    for col in df.columns:
        col_lower = col.lower()
        for candidate in candidates:
            if candidate.lower() in col_lower:
                return col

    return None


def plot_line(df, x_col, y_cols, title):
    if not y_cols:
        st.info("No hay columnas disponibles para graficar.")
        return

    if PLOTLY_AVAILABLE:
        fig = px.line(
            df,
            x=x_col,
            y=y_cols,
            markers=True,
            title=title
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        chart_df = df[[x_col] + y_cols].copy()
        chart_df = chart_df.set_index(x_col)
        st.line_chart(chart_df)


def plot_bar_from_counts(series, title):
    counts = series.value_counts().reset_index()
    counts.columns = ["categoria", "cantidad"]

    if PLOTLY_AVAILABLE:
        fig = px.bar(
            counts,
            x="categoria",
            y="cantidad",
            title=title
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(series.value_counts())


def plot_route(df):
    x_col = find_column(df, ["x"])
    z_col = find_column(df, ["z"])
    y_col = find_column(df, ["y"])

    if x_col and z_col:
        route_y_col = z_col
        y_label = "z"
    elif x_col and y_col:
        route_y_col = y_col
        y_label = "y"
    else:
        st.warning("No se encontraron columnas de posición para graficar la ruta.")
        st.write("Columnas disponibles:")
        st.write(df.columns.tolist())
        return

    route_df = df[[x_col, route_y_col]].copy()

    route_df[x_col] = pd.to_numeric(route_df[x_col], errors="coerce")
    route_df[route_y_col] = pd.to_numeric(route_df[route_y_col], errors="coerce")
    route_df = route_df.dropna()

    if route_df.empty:
        st.warning("Las columnas de posición existen, pero no contienen valores numéricos válidos.")
        return

    if PLOTLY_AVAILABLE:
        fig = px.line(
            route_df,
            x=x_col,
            y=route_y_col,
            markers=True,
            title=f"Ruta 2D del robot ({x_col}/{y_label})"
        )
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_label
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(route_df)


def get_sensor_columns(df):
    possible = [
        "temperatura",
        "temperature",
        "temp",
        "gas_ppm",
        "gas",
        "vibracion",
        "vibration",
        "inclinacion",
        "inclination",
        "bateria",
        "battery",
        "distancia_obstaculo",
        "obstacle_distance",
        "obstaculo",
    ]

    found = []

    for col in df.columns:
        col_lower = col.lower()
        for name in possible:
            if name.lower() == col_lower or name.lower() in col_lower:
                if col not in found:
                    found.append(col)

    numeric_found = []

    for col in found:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() > 0:
            numeric_found.append(col)

    return numeric_found


# CARGA DE DATOS

df_dataset = load_dataset()

unity_missions = get_unity_missions()

selected_trajectory_file = None
selected_world_file = None
df_mission = None

if unity_missions:
    mission_options = {
        f"{path.name} — modificado {pd.to_datetime(path.stat().st_mtime, unit='s').strftime('%Y-%m-%d %H:%M:%S')}": path
        for path in unity_missions
    }

    latest_label = list(mission_options.keys())[0]

    selected_label = st.sidebar.selectbox(
        "Misión exportada a Unity",
        options=list(mission_options.keys()),
        index=0
    )

    selected_trajectory_file = mission_options[selected_label]
    selected_world_file = get_matching_world_file(selected_trajectory_file)
    df_mission = load_unity_trajectory(selected_trajectory_file)

df_ros_latest, latest_ros_csv = load_latest_ros_csv()


# INTERFAZ

st.title("RescueTwin AI")
st.subheader("Dashboard de análisis, misión simulada y visualización 3D")

st.sidebar.header("Estado de archivos")

if selected_trajectory_file:
    st.sidebar.success("Misión Unity detectada")
    st.sidebar.caption(selected_trajectory_file.name)
else:
    st.sidebar.warning("No se detectaron misiones Unity")

if latest_ros_csv:
    st.sidebar.info("Último CSV ROS detectado")
    st.sidebar.caption(latest_ros_csv.name)

if not PLOTLY_AVAILABLE:
    st.sidebar.warning("Plotly no está instalado. Se usarán gráficos nativos de Streamlit.")


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dominio e hipótesis",
    "Fuentes y dataset",
    "EDA",
    "Misión simulada",
    "Unity 3D"
])


# TAB 1 - DOMINIO

with tab1:
    st.header("Dominio del negocio")

    st.write("""
    RescueTwin AI se ubica en el dominio de **robótica aplicada a emergencias,
    rescate urbano y seguridad operativa**.

    El problema principal es que, en escenarios de derrumbe, el ingreso inicial
    de rescatistas humanos puede ser peligroso por la presencia de gases,
    vibraciones estructurales, obstáculos, baja visibilidad o riesgo de nuevos colapsos.
    """)

    st.header("Hipótesis")

    st.info("""
    A partir de datos de sensores ambientales, químicos, estructurales y operativos
    de un robot cuadrúpedo, es posible predecir el nivel de riesgo de una zona de derrumbe
    y recomendar acciones que reduzcan la exposición humana.
    """)

    st.header("Propuesta de valor")

    st.write("""
    El sistema transforma datos de sensores en decisiones operativas:
    **avanzar**, **avanzar con precaución**, **cambiar ruta**, **detenerse**
    o **enviar una alerta a la base**.

    La visualización 3D en Unity permite representar la misión de forma comprensible
    para una audiencia técnica y de negocio.
    """)


# TAB 2 - FUENTES Y DATASET

with tab2:
    st.header("Fuentes de datos")

    st.write("""
    Como no existe un dataset público único que represente completamente un robot
    cuadrúpedo operando en un derrumbe real, el proyecto integra distintas fuentes
    y variables simuladas coherentes con el caso de uso.
    """)

    sources_df = pd.DataFrame([
        {
            "Fuente": "Sensores ambientales",
            "Aporte": "Temperatura, humedad, presión, sonido, luz, CO2 o partículas",
            "Uso en el proyecto": "Representar condiciones del entorno"
        },
        {
            "Fuente": "Sensores de gas",
            "Aporte": "Concentración y variación de gases",
            "Uso en el proyecto": "Detectar escenarios peligrosos para rescatistas"
        },
        {
            "Fuente": "Datos de batería",
            "Aporte": "Voltaje, autonomía, degradación o porcentaje de batería",
            "Uso en el proyecto": "Evaluar capacidad operativa del robot"
        },
        {
            "Fuente": "Búsqueda y rescate / simulación",
            "Aporte": "Escenarios de víctima, obstáculos y trayectoria",
            "Uso en el proyecto": "Construir una misión simulada realista"
        }
    ])

    st.dataframe(sources_df, use_container_width=True)

    st.header("Dataset procesado")

    if df_dataset is None:
        st.warning(f"No se encontró el dataset procesado en: {DATASET_FILE}")
    else:
        col1, col2, col3 = st.columns(3)

        col1.metric("Filas", df_dataset.shape[0])
        col2.metric("Columnas", df_dataset.shape[1])
        col3.metric("Valores nulos", int(df_dataset.isnull().sum().sum()))

        st.subheader("Vista previa")
        st.dataframe(df_dataset.head(20), use_container_width=True)

        with st.expander("Columnas del dataset"):
            st.write(df_dataset.columns.tolist())


# TAB 3 - EDA

with tab3:
    st.header("Análisis exploratorio de datos")

    if df_dataset is None:
        st.warning("No se pudo cargar el dataset para realizar el EDA.")
    else:
        numeric_cols = df_dataset.select_dtypes(include="number").columns.tolist()

        st.subheader("Resumen estadístico")

        if numeric_cols:
            st.dataframe(df_dataset[numeric_cols].describe().T, use_container_width=True)
        else:
            st.info("No se detectaron columnas numéricas.")

        st.subheader("Distribución de una variable")

        if numeric_cols:
            selected_numeric = st.selectbox(
                "Seleccionar variable numérica",
                numeric_cols
            )

            if PLOTLY_AVAILABLE:
                fig = px.histogram(
                    df_dataset,
                    x=selected_numeric,
                    nbins=30,
                    title=f"Distribución de {selected_numeric}"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(df_dataset[selected_numeric].value_counts().sort_index())
        else:
            st.info("No hay variables numéricas para graficar.")

        risk_col = find_column(df_dataset, ["riesgo", "risk", "nivel_riesgo", "risk_level"])

        if risk_col:
            st.subheader("Distribución del nivel de riesgo")
            plot_bar_from_counts(
                df_dataset[risk_col],
                "Cantidad de registros por nivel de riesgo"
            )

        st.subheader("Relación entre variables")

        if len(numeric_cols) >= 2:
            x_col = st.selectbox("Variable X", numeric_cols, index=0)
            y_col = st.selectbox("Variable Y", numeric_cols, index=1)

            if PLOTLY_AVAILABLE:
                color_col = risk_col if risk_col else None

                fig = px.scatter(
                    df_dataset,
                    x=x_col,
                    y=y_col,
                    color=color_col,
                    title=f"Relación entre {x_col} y {y_col}"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(df_dataset[[x_col, y_col]])
        else:
            st.info("Se necesitan al menos dos variables numéricas para comparar.")


# TAB 4 - MISIÓN SIMULADA

with tab4:
    st.header("Misión simulada")

    if df_mission is None or df_mission.empty:
        st.warning("No se encontró una misión exportada a Unity o no se pudo interpretar el JSON.")

        st.write("Carpeta esperada:")
        st.code(str(UNITY_STREAMING_ASSETS))

        st.write("Archivos esperados:")
        st.code("custom_mission_XXX_trajectory.json")
        st.code("custom_mission_XXX_world.json")

        st.write("Comando sugerido:")
        st.code("python3 scripts/export_mission_to_unity.py 18")

        if latest_ros_csv:
            st.info("Hay un CSV ROS reciente disponible, pero todavía no está exportado a Unity.")
            st.code(str(latest_ros_csv))

    else:
        mission_number = extract_mission_number(selected_trajectory_file)

        st.success("Misión cargada correctamente desde Unity StreamingAssets.")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Archivo de misión",
            selected_trajectory_file.name
        )

        col2.metric(
            "Número de misión",
            mission_number if mission_number else "No detectado"
        )

        col3.metric(
            "Cantidad de pasos",
            len(df_mission)
        )

        st.subheader("Resumen de estado final")

        latest = df_mission.iloc[-1]

        risk_col = find_column(df_mission, ["riesgo", "risk", "risk_level", "nivel"])
        action_col = find_column(df_mission, ["accion", "action", "decision"])
        battery_col = find_column(df_mission, ["bateria", "battery"])
        gas_col = find_column(df_mission, ["gas_ppm", "gas"])
        victim_col = find_column(df_mission, ["victima", "victim", "victima_detectada"])

        m1, m2, m3, m4 = st.columns(4)

        if risk_col:
            m1.metric("Riesgo final", risk_label(latest.get(risk_col, "N/D")))
        else:
            m1.metric("Riesgo final", "N/D")

        if action_col:
            m2.metric("Acción final", str(latest.get(action_col, "N/D"))[:35])
        else:
            m2.metric("Acción final", "N/D")

        if battery_col:
            try:
                m3.metric("Batería final", f"{float(latest.get(battery_col)):.1f}%")
            except Exception:
                m3.metric("Batería final", str(latest.get(battery_col)))
        else:
            m3.metric("Batería final", "N/D")

        if gas_col:
            try:
                m4.metric("Gas final", f"{float(latest.get(gas_col)):.1f} ppm")
            except Exception:
                m4.metric("Gas final", str(latest.get(gas_col)))
        else:
            m4.metric("Gas final", "N/D")

        if victim_col:
            victim_value = latest.get(victim_col)
            st.info(f"Estado de víctima / señal detectada: {victim_value}")

        st.subheader("Ruta 2D recorrida por el robot")
        plot_route(df_mission)

        st.subheader("Evolución de sensores durante la misión")

        sensor_cols = get_sensor_columns(df_mission)

        if sensor_cols:
            default_sensors = sensor_cols[:4]

            selected_sensors = st.multiselect(
                "Sensores a visualizar",
                sensor_cols,
                default=default_sensors
            )

            if selected_sensors:
                plot_df = df_mission.copy()

                for col in selected_sensors:
                    plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")

                x_col = "step" if "step" in plot_df.columns else plot_df.index.name

                if x_col == "step":
                    plot_line(
                        plot_df,
                        "step",
                        selected_sensors,
                        "Evolución de sensores"
                    )
                else:
                    st.line_chart(plot_df[selected_sensors])
            else:
                st.info("Seleccioná al menos un sensor.")
        else:
            st.info("No se detectaron columnas de sensores numéricos en la misión.")

        if risk_col:
            st.subheader("Distribución del riesgo durante la misión")
            plot_bar_from_counts(
                df_mission[risk_col],
                "Frecuencia de niveles de riesgo"
            )

        if action_col:
            st.subheader("Acciones recomendadas durante la misión")
            plot_bar_from_counts(
                df_mission[action_col],
                "Frecuencia de acciones recomendadas"
            )

        st.subheader("Bitácora de misión")
        st.dataframe(df_mission, use_container_width=True)

        with st.expander("Columnas detectadas en el archivo de misión"):
            st.write(df_mission.columns.tolist())


# TAB 5 - UNITY

with tab5:
    st.header("Visualización 3D en Unity")

    st.write("""
    Unity representa visualmente la misma misión que se analiza en este dashboard.
    Esto permite conectar el análisis de datos con una representación 3D del recorrido,
    los obstáculos, la detección de víctima y el estado del robot.
    """)

    st.subheader("Archivos usados por Unity")

    if selected_trajectory_file:
        st.write("Archivo de trayectoria:")
        st.code(str(selected_trajectory_file))
    else:
        st.warning("No se detectó archivo de trayectoria.")

    if selected_world_file:
        st.write("Archivo de mundo:")
        st.code(str(selected_world_file))
    else:
        st.warning("No se detectó archivo de mundo asociado.")

    st.subheader("Configuración en Unity")

    if selected_trajectory_file:
        st.write("En el componente `MissionReplayController` configurar:")
        st.code(f"Mission File Name = {selected_trajectory_file.name}")

    if selected_world_file:
        st.write("En el componente `MissionMapBuilder` configurar:")
        st.code(f"World File Name = {selected_world_file.name}")

    st.subheader("Flujo de demo recomendado")

    st.code(
        """source venv/bin/activate
python3 run_rescuetwin_full_project.py
python3 scripts/export_mission_to_unity.py 18
streamlit run app/streamlit_rescuetwin_dashboard.py"""
    )

    st.info("""
    Para una exposición estable, se puede usar una misión ya exportada,
    por ejemplo `custom_mission_018_trajectory.json`, y mostrar que tanto
    Streamlit como Unity leen la misma fuente de datos.
    """)

    if df_ros_latest is not None and latest_ros_csv is not None:
        st.subheader("Último CSV ROS detectado")

        st.write("Archivo:")
        st.code(str(latest_ros_csv))

        st.dataframe(df_ros_latest.head(20), use_container_width=True)