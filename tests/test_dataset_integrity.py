from pathlib import Path

import pandas as pd


def test_processed_dataset_exists(project_root: Path):
    dataset_path = project_root / "data" / "processed" / "rescuetwin_dataset.csv"

    assert dataset_path.exists(), (
        "No se encontró data/processed/rescuetwin_dataset.csv. "
        "Ejecutá primero el notebook de exploración/preparación de fuentes."
    )


def test_processed_dataset_has_rows(project_root: Path):
    dataset_path = project_root / "data" / "processed" / "rescuetwin_dataset.csv"
    df = pd.read_csv(dataset_path)

    assert len(df) > 0, "El dataset integrado existe pero no tiene registros."
    assert df.shape[1] > 0, "El dataset integrado existe pero no tiene columnas."


def test_dataset_required_columns(project_root: Path):
    dataset_path = project_root / "data" / "processed" / "rescuetwin_dataset.csv"
    df = pd.read_csv(dataset_path)

    required_columns = [
        "nivel_riesgo",
        "temperatura",
        "gas_ppm",
        "vibracion",
        "inclinacion",
        "distancia_obstaculo",
        "bateria",
        "persona_detectada",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    assert not missing, f"Faltan columnas requeridas en el dataset: {missing}"


def test_target_has_expected_classes(project_root: Path):
    dataset_path = project_root / "data" / "processed" / "rescuetwin_dataset.csv"
    df = pd.read_csv(dataset_path)

    expected_classes = {"Bajo", "Medio", "Alto"}
    actual_classes = set(df["nivel_riesgo"].dropna().unique())

    assert actual_classes.issubset(expected_classes), (
        f"La variable nivel_riesgo tiene clases inesperadas: {actual_classes - expected_classes}"
    )

    assert len(actual_classes) >= 2, (
        "La variable nivel_riesgo debería tener al menos dos clases para entrenar/evaluar el modelo."
    )


def test_dataset_without_null_target(project_root: Path):
    dataset_path = project_root / "data" / "processed" / "rescuetwin_dataset.csv"
    df = pd.read_csv(dataset_path)

    null_target_count = df["nivel_riesgo"].isnull().sum()

    assert null_target_count == 0, (
        f"La variable objetivo nivel_riesgo tiene {null_target_count} valores nulos."
    )
