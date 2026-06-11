from pathlib import Path


def test_project_main_folders_exist(project_root: Path):
    expected_dirs = [
        "data",
        "models",
        "notebooks",
        "reports",
        "ros2_ws",
        "scripts",
        "app",
    ]

    missing = [
        folder for folder in expected_dirs
        if not (project_root / folder).exists()
    ]

    assert not missing, f"Faltan carpetas principales del proyecto: {missing}"


def test_core_project_files_exist(project_root: Path):
    expected_files = [
        "README.md",
        "requirements.txt",
        "run_rescuetwin_full_project.py",
        "scripts/generate_mission_report.py",
        "scripts/visualize_mission_route.py",
    ]

    missing = [
        file for file in expected_files
        if not (project_root / file).exists()
    ]

    assert not missing, f"Faltan archivos principales del proyecto: {missing}"


def test_notebooks_exist(project_root: Path):
    expected_notebooks = [
        "notebooks/01_exploracion_fuentes.ipynb",
        "notebooks/02_eda_rescuetwin.ipynb",
        "notebooks/03_modelado_rescuetwin.ipynb",
    ]

    missing = [
        notebook for notebook in expected_notebooks
        if not (project_root / notebook).exists()
    ]

    assert not missing, f"Faltan notebooks esperados: {missing}"
