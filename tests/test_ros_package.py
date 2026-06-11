from pathlib import Path


def test_ros_package_files_exist(project_root: Path):
    package_dir = project_root / "ros2_ws" / "src" / "rescuetwin_sim"
    module_dir = package_dir / "rescuetwin_sim"

    expected_files = [
        package_dir / "package.xml",
        package_dir / "setup.py",
        module_dir / "__init__.py",
        module_dir / "motion_node.py",
        module_dir / "sensor_sim_node.py",
        module_dir / "risk_ai_node.py",
        module_dir / "decision_node.py",
        module_dir / "mission_logger_node.py",
    ]

    missing = [str(path.relative_to(project_root)) for path in expected_files if not path.exists()]

    assert not missing, f"Faltan archivos del paquete ROS: {missing}"


def test_setup_py_entry_points(project_root: Path):
    setup_py = project_root / "ros2_ws" / "src" / "rescuetwin_sim" / "setup.py"

    content = setup_py.read_text(encoding="utf-8")

    expected_entry_points = [
        "motion_node = rescuetwin_sim.motion_node:main",
        "sensor_sim_node = rescuetwin_sim.sensor_sim_node:main",
        "risk_ai_node = rescuetwin_sim.risk_ai_node:main",
        "decision_node = rescuetwin_sim.decision_node:main",
        "mission_logger_node = rescuetwin_sim.mission_logger_node:main",
    ]

    missing = [entry for entry in expected_entry_points if entry not in content]

    assert not missing, f"Faltan entry_points en setup.py: {missing}"


def test_gazebo_world_exists(project_root: Path):
    world_path = (
        project_root
        / "ros2_ws"
        / "src"
        / "rescuetwin_sim"
        / "worlds"
        / "collapse_world.world"
    )

    assert world_path.exists(), "No se encontró el mundo Gazebo collapse_world.world"
