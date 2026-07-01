from pathlib import Path

import pandas as pd
import pytest


def test_mission_logs_folder_exists(project_root: Path):
    logs_dir = project_root / "reports" / "mission_logs"

    assert logs_dir.exists(), "No existe reports/mission_logs"



def test_mission_report_script_exists(project_root: Path):
    script_path = project_root / "scripts" / "generate_mission_report.py"

    assert script_path.exists(), "No existe scripts/generate_mission_report.py"
