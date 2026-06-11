from pathlib import Path

import pandas as pd
import pytest


def test_mission_logs_folder_exists(project_root: Path):
    logs_dir = project_root / "reports" / "mission_logs"

    assert logs_dir.exists(), "No existe reports/mission_logs"


def test_latest_mission_log_has_expected_columns(project_root: Path):
    logs_dir = project_root / "reports" / "mission_logs"
    csv_files = sorted(logs_dir.glob("ros_mission_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not csv_files:
        pytest.skip(
            "No hay logs ros_mission_*.csv todavía. "
            "Ejecutá run_rescuetwin_full_project.py para generar una bitácora."
        )

    latest_csv = csv_files[0]
    df = pd.read_csv(latest_csv)

    expected_columns = [
        "timestamp",
        "x",
        "y",
        "mission_state",
        "risk_level",
        "temperature",
        "gas_ppm",
        "battery",
        "decision_status",
    ]

    missing = [col for col in expected_columns if col not in df.columns]

    assert not missing, f"El log {latest_csv.name} no tiene columnas esperadas: {missing}"
    assert len(df) > 0, f"El log {latest_csv.name} está vacío."


def test_mission_report_script_exists(project_root: Path):
    script_path = project_root / "scripts" / "generate_mission_report.py"

    assert script_path.exists(), "No existe scripts/generate_mission_report.py"
