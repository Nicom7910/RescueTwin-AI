from pathlib import Path

import joblib
import pandas as pd


def test_model_files_exist(project_root: Path):
    model_path = project_root / "models" / "random_forest_rescuetwin.pkl"
    columns_path = project_root / "models" / "model_columns.pkl"

    assert model_path.exists(), "No se encontró models/random_forest_rescuetwin.pkl"
    assert columns_path.exists(), "No se encontró models/model_columns.pkl"


def test_model_and_columns_load(project_root: Path):
    model_path = project_root / "models" / "random_forest_rescuetwin.pkl"
    columns_path = project_root / "models" / "model_columns.pkl"

    model = joblib.load(model_path)
    columns = joblib.load(columns_path)

    assert model is not None, "El modelo cargado es None."
    assert isinstance(columns, list), "model_columns.pkl debería contener una lista de columnas."
    assert len(columns) > 0, "model_columns.pkl está vacío."


def test_model_can_predict_with_sample(project_root: Path):
    model_path = project_root / "models" / "random_forest_rescuetwin.pkl"
    columns_path = project_root / "models" / "model_columns.pkl"

    model = joblib.load(model_path)
    columns = joblib.load(columns_path)

    sample = pd.DataFrame([{col: 0 for col in columns}])

    # Valores representativos de una situación de riesgo medio/bajo.
    sample_values = {
        "temperatura": 28.0,
        "humedad": 55.0,
        "presion": 1013.0,
        "luz": 45.0,
        "sonido_db": 50.0,
        "co2": 900.0,
        "particulas_pm25": 45.0,
        "gas_ppm": 80.0,
        "vibracion": 0.5,
        "inclinacion": 8.0,
        "distancia_obstaculo": 3.0,
        "velocidad_robot": 0.5,
        "senal_comunicacion": 80.0,
        "bateria": 85.0,
        "voltaje_bateria": 12.1,
        "temperatura_bateria": 32.0,
        "autonomia_estimada_min": 45.0,
        "visibilidad": 70.0,
        "persona_detectada": 0,
        "confianza_persona": 0.2,
    }

    for col, value in sample_values.items():
        if col in sample.columns:
            sample[col] = value

    prediction = model.predict(sample)[0]

    expected_classes = {"Bajo", "Medio", "Alto"}

    assert prediction in expected_classes, (
        f"El modelo devolvió una clase inesperada: {prediction}"
    )
