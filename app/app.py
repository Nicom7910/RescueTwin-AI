import os
import joblib
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


# ==========================
# Configuración general
# ==========================

st.set_page_config(
    page_title="RescueTwin AI",
    page_icon="🤖",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "rescuetwin_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "random_forest_rescuetwin.pkl")
COLUMNS_PATH = os.path.join(BASE_DIR, "models", "model_columns.pkl")


# ==========================
# Funciones auxiliares
# ==========================

@st.cache_data
def cargar_dataset():
    return pd.read_csv(DATA_PATH)


@st.cache_resource
def cargar_modelo():
    modelo = joblib.load(MODEL_PATH)
    columnas = joblib.load(COLUMNS_PATH)
    return modelo, columnas


def recomendar_accion(nivel_riesgo, persona_detectada):
    if nivel_riesgo == "Bajo" and persona_detectada == 0:
        return "Avanzar"

    if nivel_riesgo == "Bajo" and persona_detectada == 1:
        return "Enviar alerta y continuar exploración"

    if nivel_riesgo == "Medio" and persona_detectada == 0:
        return "Avanzar con precaución"

    if nivel_riesgo == "Medio" and persona_detectada == 1:
        return "Enviar alerta y avanzar con precaución"

    if nivel_riesgo == "Alto" and persona_detectada == 0:
        return "Cambiar ruta o detenerse"

    if nivel_riesgo == "Alto" and persona_detectada == 1:
        return "Enviar alerta y cambiar ruta"

    return "Revisar manualmente"


def preparar_entrada(datos_usuario, columnas_modelo):
    df_input = pd.DataFrame([datos_usuario])

    df_input = pd.get_dummies(df_input, columns=["gas_tipo"], drop_first=True)

    for col in columnas_modelo:
        if col not in df_input.columns:
            df_input[col] = 0

    df_input = df_input[columnas_modelo]

    return df_input


def obtener_color_riesgo(riesgo):
    if riesgo == "Bajo":
        return "🟢"
    if riesgo == "Medio":
        return "🟡"
    if riesgo == "Alto":
        return "🔴"
    return "⚪"


# ==========================
# Carga de datos y modelo
# ==========================

try:
    df = cargar_dataset()
    modelo, columnas_modelo = cargar_modelo()
except Exception as e:
    st.error("No se pudieron cargar los archivos necesarios.")
    st.write("Verificá que existan:")
    st.code("""
data/processed/rescuetwin_dataset.csv
models/random_forest_rescuetwin.pkl
models/model_columns.pkl
""")
    st.exception(e)
    st.stop()


# ==========================
# Sidebar
# ==========================

st.sidebar.title("🤖 RescueTwin AI")
st.sidebar.write("Gemelo digital de un robot cuadrúpedo para rescate en derrumbes.")

pagina = st.sidebar.radio(
    "Seleccionar sección",
    [
        "Panel de predicción",
        "Simulador de recorrido",
        "Dashboard de datos",
        "Información del proyecto"
    ]
)


# ==========================
# Página 1: Panel de predicción
# ==========================

if pagina == "Panel de predicción":
    st.title("🤖 Panel de predicción de riesgo")
    st.write(
        "Ingresá los valores de sensores del robot para predecir el nivel de riesgo "
        "de una zona de derrumbe."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Sensores ambientales")

        temperatura = st.slider("Temperatura ambiental (°C)", 0.0, 60.0, 28.0, 0.5)
        humedad = st.slider("Humedad (%)", 0.0, 100.0, 55.0, 1.0)
        presion = st.slider("Presión (hPa)", 900.0, 1100.0, 1013.0, 1.0)
        luz = st.slider("Luz / iluminación", 0.0, 100.0, 40.0, 1.0)
        sonido_db = st.slider("Sonido (dB)", 0.0, 120.0, 50.0, 1.0)
        co2 = st.slider("CO₂ (ppm)", 300.0, 5000.0, 900.0, 50.0)
        particulas_pm25 = st.slider("Partículas PM2.5", 0.0, 300.0, 40.0, 1.0)

    with col2:
        st.subheader("Sensores de riesgo")

        gas_tipo = st.selectbox(
            "Tipo de gas detectado",
            [
                "sin_gas",
                "metano",
                "monoxido_carbono",
                "amoniaco",
                "humo",
                "gas_desconocido"
            ]
        )

        gas_ppm = st.slider("Concentración de gas (ppm)", 0.0, 500.0, 80.0, 5.0)
        vibracion = st.slider("Vibración estructural", 0.0, 2.5, 0.5, 0.05)
        inclinacion = st.slider("Inclinación del terreno", 0.0, 35.0, 8.0, 0.5)
        distancia_obstaculo = st.slider("Distancia a obstáculo (m)", 0.2, 5.0, 2.0, 0.1)
        visibilidad = st.slider("Visibilidad (%)", 0.0, 100.0, 70.0, 1.0)

    with col3:
        st.subheader("Estado del robot")

        velocidad_robot = st.slider("Velocidad del robot (m/s)", 0.1, 1.5, 0.7, 0.1)
        senal_comunicacion = st.slider("Señal de comunicación (%)", 20.0, 100.0, 80.0, 1.0)
        bateria = st.slider("Batería restante (%)", 15.0, 100.0, 75.0, 1.0)
        voltaje_bateria = st.slider("Voltaje de batería", 10.5, 12.6, 12.0, 0.1)
        temperatura_bateria = st.slider("Temperatura de batería (°C)", 0.0, 70.0, 30.0, 0.5)
        autonomia_estimada_min = st.slider("Autonomía estimada (min)", 0.0, 80.0, 45.0, 1.0)

        persona_detectada = st.selectbox(
            "¿Se detectó una posible persona?",
            [0, 1],
            format_func=lambda x: "No" if x == 0 else "Sí"
        )

        confianza_persona = st.slider("Confianza de detección", 0.0, 1.0, 0.2, 0.01)

    datos_usuario = {
        "temperatura": temperatura,
        "humedad": humedad,
        "presion": presion,
        "luz": luz,
        "sonido_db": sonido_db,
        "co2": co2,
        "particulas_pm25": particulas_pm25,
        "gas_tipo": gas_tipo,
        "gas_ppm": gas_ppm,
        "vibracion": vibracion,
        "inclinacion": inclinacion,
        "distancia_obstaculo": distancia_obstaculo,
        "velocidad_robot": velocidad_robot,
        "senal_comunicacion": senal_comunicacion,
        "bateria": bateria,
        "voltaje_bateria": voltaje_bateria,
        "temperatura_bateria": temperatura_bateria,
        "autonomia_estimada_min": autonomia_estimada_min,
        "visibilidad": visibilidad,
        "persona_detectada": persona_detectada,
        "confianza_persona": confianza_persona
    }

    st.divider()

    if st.button("Evaluar riesgo", type="primary"):
        entrada_modelo = preparar_entrada(datos_usuario, columnas_modelo)

        prediccion = modelo.predict(entrada_modelo)[0]
        probabilidades = modelo.predict_proba(entrada_modelo)[0]

        accion = recomendar_accion(prediccion, persona_detectada)

        icono = obtener_color_riesgo(prediccion)

        st.subheader("Resultado de la evaluación")

        col_res1, col_res2, col_res3 = st.columns(3)

        with col_res1:
            st.metric("Nivel de riesgo", f"{icono} {prediccion}")

        with col_res2:
            st.metric("Acción recomendada", accion)

        with col_res3:
            st.metric("Persona detectada", "Sí" if persona_detectada == 1 else "No")

        proba_df = pd.DataFrame({
            "Nivel de riesgo": modelo.classes_,
            "Probabilidad": probabilidades
        })

        fig = px.bar(
            proba_df,
            x="Nivel de riesgo",
            y="Probabilidad",
            title="Probabilidad estimada por clase",
            text_auto=".2f"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.info(
            "Interpretación: el sistema utiliza los sensores ingresados para estimar "
            "si la zona representa un riesgo bajo, medio o alto para el avance del robot."
        )


# ==========================
# Página 2: Simulador de recorrido
# ==========================

elif pagina == "Simulador de recorrido":
    st.title("🗺️ Simulador de recorrido del robot")

    st.write(
        "Esta sección simula un recorrido del robot por distintas zonas del derrumbe "
        "y predice el nivel de riesgo en cada punto."
    )

    cantidad_zonas = st.slider("Cantidad de zonas a simular", 5, 20, 10)

    zonas_posibles = [
        "Entrada",
        "Pasillo A",
        "Pasillo B",
        "Escalera colapsada",
        "Sector norte",
        "Sector sur",
        "Zona de escombros",
        "Habitación bloqueada",
        "Túnel estrecho",
        "Punto crítico"
    ]

    recorrido = df.sample(cantidad_zonas, random_state=np.random.randint(0, 10000)).copy()
    recorrido["paso"] = range(1, cantidad_zonas + 1)
    recorrido["zona_simulada"] = np.random.choice(zonas_posibles, size=cantidad_zonas)

    X_recorrido = recorrido.drop(columns=["zona", "nivel_riesgo", "accion_recomendada"])
    X_recorrido = pd.get_dummies(X_recorrido, columns=["gas_tipo"], drop_first=True)

    for col in columnas_modelo:
        if col not in X_recorrido.columns:
            X_recorrido[col] = 0

    X_recorrido = X_recorrido[columnas_modelo]

    recorrido["riesgo_predicho"] = modelo.predict(X_recorrido)

    recorrido["accion_predicha"] = recorrido.apply(
        lambda row: recomendar_accion(row["riesgo_predicho"], row["persona_detectada"]),
        axis=1
    )

    st.subheader("Recorrido simulado")

    st.dataframe(
        recorrido[
            [
                "paso",
                "zona_simulada",
                "temperatura",
                "gas_ppm",
                "vibracion",
                "inclinacion",
                "bateria",
                "visibilidad",
                "persona_detectada",
                "riesgo_predicho",
                "accion_predicha"
            ]
        ],
        use_container_width=True
    )

    mapa_riesgo = {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3
    }

    recorrido["riesgo_num"] = recorrido["riesgo_predicho"].map(mapa_riesgo)

    fig = px.line(
        recorrido,
        x="paso",
        y="riesgo_num",
        markers=True,
        title="Evolución del riesgo durante el recorrido",
        labels={
            "paso": "Paso del recorrido",
            "riesgo_num": "Nivel de riesgo"
        }
    )

    fig.update_yaxes(
        tickvals=[1, 2, 3],
        ticktext=["Bajo", "Medio", "Alto"]
    )

    st.plotly_chart(fig, use_container_width=True)

    zonas_altas = recorrido[recorrido["riesgo_predicho"] == "Alto"]

    if len(zonas_altas) > 0:
        st.warning(
            f"Se detectaron {len(zonas_altas)} zona(s) de riesgo alto. "
            "El sistema recomienda revisar el recorrido antes de continuar."
        )
    else:
        st.success("No se detectaron zonas de riesgo alto en este recorrido simulado.")


# ==========================
# Página 3: Dashboard
# ==========================

elif pagina == "Dashboard de datos":
    st.title("📊 Dashboard de datos")

    st.write(
        "Visualización general del dataset integrado utilizado para entrenar el modelo."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Registros", df.shape[0])

    with col2:
        st.metric("Variables", df.shape[1])

    with col3:
        st.metric("Clases de riesgo", df["nivel_riesgo"].nunique())

    st.divider()

    fig_riesgo = px.histogram(
        df,
        x="nivel_riesgo",
        title="Distribución de niveles de riesgo",
        category_orders={"nivel_riesgo": ["Bajo", "Medio", "Alto"]}
    )

    st.plotly_chart(fig_riesgo, use_container_width=True)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_gas = px.box(
            df,
            x="nivel_riesgo",
            y="gas_ppm",
            title="Concentración de gas por nivel de riesgo",
            category_orders={"nivel_riesgo": ["Bajo", "Medio", "Alto"]}
        )
        st.plotly_chart(fig_gas, use_container_width=True)

    with col_g2:
        fig_vib = px.box(
            df,
            x="nivel_riesgo",
            y="vibracion",
            title="Vibración por nivel de riesgo",
            category_orders={"nivel_riesgo": ["Bajo", "Medio", "Alto"]}
        )
        st.plotly_chart(fig_vib, use_container_width=True)

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        fig_inc = px.box(
            df,
            x="nivel_riesgo",
            y="inclinacion",
            title="Inclinación por nivel de riesgo",
            category_orders={"nivel_riesgo": ["Bajo", "Medio", "Alto"]}
        )
        st.plotly_chart(fig_inc, use_container_width=True)

    with col_g4:
        fig_vis = px.box(
            df,
            x="nivel_riesgo",
            y="visibilidad",
            title="Visibilidad por nivel de riesgo",
            category_orders={"nivel_riesgo": ["Bajo", "Medio", "Alto"]}
        )
        st.plotly_chart(fig_vis, use_container_width=True)

    st.subheader("Acciones recomendadas")

    fig_acciones = px.histogram(
        df,
        y="accion_recomendada",
        title="Distribución de acciones recomendadas"
    )

    st.plotly_chart(fig_acciones, use_container_width=True)


# ==========================
# Página 4: Información del proyecto
# ==========================

elif pagina == "Información del proyecto":
    st.title("ℹ️ Información del proyecto")

    st.subheader("Nombre del proyecto")
    st.write("**RescueTwin AI: Gemelo digital de un robot cuadrúpedo para rescate en derrumbes**")

    st.subheader("Problema")
    st.write(
        "En zonas de derrumbe, enviar personal humano a inspeccionar puede ser muy peligroso. "
        "El robot cuadrúpedo permite recolectar información del entorno antes de que ingrese "
        "un equipo de rescate."
    )

    st.subheader("Hipótesis")
    st.write(
        "A partir de datos de sensores ambientales, estructurales y operativos de un robot cuadrúpedo, "
        "es posible predecir el nivel de riesgo de una zona de derrumbe y recomendar acciones que "
        "reduzcan la exposición del personal de rescate."
    )

    st.subheader("Variables utilizadas")
    st.write(
        "El modelo utiliza variables como temperatura, humedad, CO₂, partículas, gas, vibración, "
        "inclinación, distancia a obstáculos, batería, visibilidad, señal de comunicación y detección "
        "de personas."
    )

    st.subheader("Modelo utilizado")
    st.write(
        "Se utilizó un modelo Random Forest Classifier, ya que permite resolver problemas de clasificación "
        "y analizar la importancia de las variables en la predicción."
    )

    st.subheader("Valor para el negocio")
    st.write(
        "La solución ayuda a equipos de rescate, bomberos y defensa civil a tomar decisiones basadas en datos, "
        "priorizando la seguridad humana y mejorando la planificación del recorrido del robot."
    )