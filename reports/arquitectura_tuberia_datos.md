# Arquitectura / Tubería de Datos - RescueTwin AI

## Flujo general

Fuentes públicas + datos simulados
↓
Integración de variables ambientales, químicas, estructurales y operativas
↓
Dataset final: data/processed/rescuetwin_dataset.csv
↓
Análisis Exploratorio de Datos
↓
Entrenamiento del modelo Random Forest
↓
Artefactos del modelo: models/random_forest_rescuetwin.pkl y models/model_columns.pkl
↓
Simulación ROS 2 del robot cuadrúpedo
↓
Predicción del nivel de riesgo
↓
Nodo de decisión autónoma
↓
Dashboard Streamlit, reportes de misión, alertas y visualización de ruta
