import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


# ============================================================
# Configuración general
# ============================================================

st.set_page_config(
    page_title="RescueTwin AI Dashboard",
    page_icon="🤖",
    layout="wide",
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_DIR / "reports" / "mission_logs"
FIGURES_DIR = PROJECT_DIR / "reports" / "figures"
MODELS_DIR = PROJECT_DIR / "models"


# ============================================================
# Utilidades
# ============================================================

def get_latest_csv() -> Path | None:
    if not LOG_DIR.exists():
        return None

    csv_files = sorted(
        LOG_DIR.glob("ros_mission_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not csv_files:
        csv_files = sorted(
            LOG_DIR.glob("mission_realistic_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    return csv_files[0] if csv_files else None


def load_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Normalización defensiva de columnas por si algún CSV viene con nombres distintos.
    rename_map = {
        "risk": "risk_level",
        "gas": "gas_ppm",
        "vibration": "vibration",
        "battery": "battery",
        "obstacle": "obstacle_distance",
        "person": "person_detected",
    }

    df = df.rename(columns=rename_map)

    numeric_cols = [
        "x", "y", "z",
        "temperature", "gas_ppm", "vibration", "inclination",
        "battery", "obstacle_distance", "person_detected",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return df


def risk_score(value: str) -> int:
    mapping = {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3,
        "Desconocido": 0,
    }
    return mapping.get(str(value), 0)


def risk_label_from_score(score: int) -> str:
    mapping = {
        1: "Bajo",
        2: "Medio",
        3: "Alto",
    }
    return mapping.get(int(score), "Desconocido")


def metric_value(df: pd.DataFrame, column: str, default="N/D"):
    if column not in df.columns or df.empty:
        return default

    value = df[column].dropna()
    if value.empty:
        return default

    return value.iloc[-1]


def count_alerts(df: pd.DataFrame) -> int:
    if "last_alert" not in df.columns:
        return 0

    alerts = df["last_alert"].dropna().astype(str)
    alerts = alerts[alerts != "SIN_ALERTAS"]

    return alerts.nunique()


def get_mission_result(df: pd.DataFrame) -> str:
    if df.empty:
        return "Sin datos"

    if "mission_state" not in df.columns:
        return "Misión registrada"

    final_state = str(df["mission_state"].dropna().iloc[-1])

    if final_state == "VICTIMA_DETECTADA":
        return "Víctima detectada"
    if final_state == "MISION_ABORTADA":
        return "Misión abortada por seguridad"
    if final_state == "MISION_COMPLETADA":
        return "Misión completada"
    if final_state == "RETORNANDO_BASE":
        return "Retorno a base"
    if final_state == "EVITANDO_RIESGO":
        return "Evitando zona de riesgo"

    return final_state


def find_latest_route_image() -> Path | None:
    if not LOG_DIR.exists():
        return None

    images = sorted(
        LOG_DIR.glob("mission_route_*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return images[0] if images else None


def plot_route(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 6))

    if "x" in df.columns and "y" in df.columns:
        ax.plot(df["x"], df["y"], marker="o", linewidth=2, label="Ruta del robot")

        if not df.empty:
            ax.scatter(df["x"].iloc[0], df["y"].iloc[0], s=120, marker="s", label="Inicio")
            ax.scatter(df["x"].iloc[-1], df["y"].iloc[-1], s=160, marker="*", label="Fin")

    zones = [
        ("Entrada", -3.0, 0.0),
        ("Escombros", 1.5, 0.8),
        ("Riesgo medio", 3.0, -2.8),
        ("Riesgo alto", 5.0, 2.8),
        ("Víctima probable", 7.0, 2.6),
    ]

    for name, x, y in zones:
        ax.scatter([x], [y], s=120)
        ax.text(x + 0.1, y + 0.1, name)

    if "risk_level" in df.columns:
        high = df[df["risk_level"].astype(str) == "Alto"]
        if not high.empty:
            ax.scatter(
                high["x"],
                high["y"],
                s=220,
                facecolors="none",
                edgecolors="red",
                linewidths=2,
                label="Riesgo alto",
            )

    if "person_detected" in df.columns:
        victim = df[df["person_detected"] == 1]
        if not victim.empty:
            ax.scatter(
                victim["x"],
                victim["y"],
                s=260,
                facecolors="none",
                edgecolors="green",
                linewidths=2,
                label="Persona detectada",
            )

    ax.set_title("Ruta 2D de misión")
    ax.set_xlabel("Posición X")
    ax.set_ylabel("Posición Y")
    ax.grid(True, alpha=0.3)
    ax.axis("equal")
    ax.legend()

    return fig


def line_chart(df: pd.DataFrame, column: str, title: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(9, 4))

    if column not in df.columns:
        ax.text(0.5, 0.5, f"No existe la columna {column}", ha="center", va="center")
        ax.set_axis_off()
        return fig

    x = range(len(df))
    ax.plot(x, df[column], marker="o", linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Lectura de misión")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    return fig


def risk_timeline_chart(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4))

    if "risk_level" not in df.columns:
        ax.text(0.5, 0.5, "No existe la columna risk_level", ha="center", va="center")
        ax.set_axis_off()
        return fig

    scores = df["risk_level"].astype(str).apply(risk_score)
    ax.plot(range(len(df)), scores, marker="o", linewidth=2)
    ax.set_title("Evolución del riesgo IA")
    ax.set_xlabel("Lectura de misión")
    ax.set_ylabel("Nivel de riesgo")
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["N/D", "Bajo", "Medio", "Alto"])
    ax.grid(True, alpha=0.3)

    return fig


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("🤖 RescueTwin AI")
st.sidebar.caption("Dashboard de misión y gemelo digital")

latest_csv = get_latest_csv()

uploaded_file = st.sidebar.file_uploader(
    "Cargar CSV de misión",
    type=["csv"],
    help="Opcional. Si no cargás nada, se usa el último CSV de reports/mission_logs.",
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    csv_name = uploaded_file.name
else:
    if latest_csv is None:
        df = pd.DataFrame()
        csv_name = "Sin CSV disponible"
    else:
        df = load_csv(latest_csv)
        csv_name = str(latest_csv.relative_to(PROJECT_DIR))

st.sidebar.divider()
st.sidebar.write("**Archivo usado:**")
st.sidebar.code(csv_name)

st.sidebar.write("**Carpeta logs:**")
st.sidebar.code(str(LOG_DIR.relative_to(PROJECT_DIR)))

st.sidebar.divider()

if st.sidebar.button("Actualizar dashboard"):
    st.rerun()


# ============================================================
# Header
# ============================================================

st.title("🤖 RescueTwin AI — Dashboard de Misión")
st.markdown(
    """
    Panel de visualización para el **gemelo digital de un robot cuadrúpedo de rescate en derrumbes**.
    Permite analizar la misión, sensores simulados, riesgo IA, decisiones autónomas, alertas y ruta recorrida.
    """
)

if df.empty:
    st.warning(
        "No se encontró ningún CSV de misión. Primero ejecutá el sistema completo para generar logs:\n\n"
        "`python3 run_rescuetwin_full_project.py --duration 60`"
    )
    st.stop()


# ============================================================
# KPIs
# ============================================================

final_risk = metric_value(df, "risk_level", "Desconocido")
final_action = metric_value(df, "recommended_action", "N/D")
final_state = metric_value(df, "mission_state", "N/D")
final_battery = metric_value(df, "battery", None)
final_gas = metric_value(df, "gas_ppm", None)
final_temp = metric_value(df, "temperature", None)
mission_result = get_mission_result(df)

if "risk_level" in df.columns:
    max_risk_score = df["risk_level"].astype(str).apply(risk_score).max()
    max_risk = risk_label_from_score(max_risk_score)
else:
    max_risk = "Desconocido"

alerts_count = count_alerts(df)
person_detected = int(df["person_detected"].max()) if "person_detected" in df.columns else 0

st.subheader("Resumen ejecutivo")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Resultado", mission_result)
col2.metric("Riesgo final", str(final_risk))
col3.metric("Riesgo máximo", str(max_risk))
col4.metric("Alertas", alerts_count)

col5, col6, col7, col8 = st.columns(4)

col5.metric("Estado final", str(final_state))
col6.metric("Batería final", f"{final_battery:.1f}%" if final_battery is not None else "N/D")
col7.metric("Gas final", f"{final_gas:.1f} ppm" if final_gas is not None else "N/D")
col8.metric("Persona detectada", "Sí" if person_detected == 1 else "No")

st.info(f"**Última acción recomendada:** {final_action}")


# ============================================================
# Tabs
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📍 Ruta 2D",
        "📊 Sensores",
        "🧠 Riesgo IA",
        "🚨 Alertas y decisiones",
        "📄 Bitácora",
    ]
)


# ============================================================
# Tab ruta
# ============================================================

with tab1:
    st.subheader("Ruta recorrida por el robot")

    route_image = find_latest_route_image()

    if route_image is not None:
        st.caption(f"Imagen generada: `{route_image.relative_to(PROJECT_DIR)}`")
        st.image(str(route_image), use_container_width=True)
    else:
        st.caption("No se encontró imagen previa. Se genera una ruta directamente desde el CSV.")
        st.pyplot(plot_route(df), use_container_width=True)

    with st.expander("Ver datos de posición"):
        cols = [c for c in ["timestamp", "x", "y", "z", "mission_state", "risk_level"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)


# ============================================================
# Tab sensores
# ============================================================

with tab2:
    st.subheader("Evolución de sensores de misión")

    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.pyplot(line_chart(df, "temperature", "Temperatura", "°C"), use_container_width=True)

    with chart_cols[1]:
        st.pyplot(line_chart(df, "gas_ppm", "Gas detectado", "ppm"), use_container_width=True)

    chart_cols_2 = st.columns(2)

    with chart_cols_2[0]:
        st.pyplot(line_chart(df, "vibration", "Vibración estructural", "Nivel"), use_container_width=True)

    with chart_cols_2[1]:
        st.pyplot(line_chart(df, "inclination", "Inclinación del robot", "Grados"), use_container_width=True)

    chart_cols_3 = st.columns(2)

    with chart_cols_3[0]:
        st.pyplot(line_chart(df, "battery", "Batería", "%"), use_container_width=True)

    with chart_cols_3[1]:
        st.pyplot(line_chart(df, "obstacle_distance", "Distancia a obstáculo", "m"), use_container_width=True)


# ============================================================
# Tab riesgo
# ============================================================

with tab3:
    st.subheader("Predicción de riesgo IA")

    st.pyplot(risk_timeline_chart(df), use_container_width=True)

    if "risk_level" in df.columns:
        risk_counts = df["risk_level"].astype(str).value_counts().reset_index()
        risk_counts.columns = ["Nivel de riesgo", "Cantidad"]

        st.write("Distribución de niveles de riesgo:")
        st.dataframe(risk_counts, use_container_width=True)

        st.bar_chart(
            risk_counts,
            x="Nivel de riesgo",
            y="Cantidad",
            use_container_width=True,
        )

    if "recommended_action" in df.columns:
        st.write("Acciones recomendadas registradas:")
        action_counts = df["recommended_action"].astype(str).value_counts().reset_index()
        action_counts.columns = ["Acción recomendada", "Cantidad"]
        st.dataframe(action_counts, use_container_width=True)


# ============================================================
# Tab alertas
# ============================================================

with tab4:
    st.subheader("Alertas a la base y decisiones autónomas")

    if "last_alert" in df.columns:
        alerts = df[["timestamp", "last_alert"]].copy() if "timestamp" in df.columns else df[["last_alert"]].copy()
        alerts = alerts.dropna()
        alerts = alerts[alerts["last_alert"].astype(str) != "SIN_ALERTAS"]

        if alerts.empty:
            st.success("No se registraron alertas críticas durante la misión.")
        else:
            st.dataframe(alerts.drop_duplicates(), use_container_width=True)
    else:
        st.warning("El CSV no contiene columna `last_alert`.")

    st.divider()

    if "decision_status" in df.columns:
        st.write("Decisiones autónomas:")
        decision_cols = [c for c in ["timestamp", "mission_state", "risk_level", "decision_status"] if c in df.columns]
        st.dataframe(df[decision_cols].tail(20), use_container_width=True)
    else:
        st.warning("El CSV no contiene columna `decision_status`.")


# ============================================================
# Tab bitácora
# ============================================================

with tab5:
    st.subheader("Bitácora completa de misión")

    st.write(f"Registros: **{len(df)}**")
    st.dataframe(df, use_container_width=True)

    csv_download = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar CSV filtrado",
        data=csv_download,
        file_name="rescuetwin_mission_dashboard.csv",
        mime="text/csv",
    )


# ============================================================
# Footer técnico
# ============================================================

st.divider()

with st.expander("Información técnica del proyecto"):
    st.markdown(
        f"""
        **Directorio del proyecto:** `{PROJECT_DIR}`  
        **Directorio de logs:** `{LOG_DIR}`  
        **Directorio de modelos:** `{MODELS_DIR}`  

        Archivos esperados del modelo:

        - `models/random_forest_rescuetwin.pkl`
        - `models/model_columns.pkl`

        Para generar nuevos datos:

        ```bash
        python3 run_rescuetwin_full_project.py --duration 60
        ```

        Para generar visualización 2D manualmente:

        ```bash
        python3 scripts/visualize_mission_route.py
        ```
        """
    )
