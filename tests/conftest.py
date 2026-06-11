from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """
    Devuelve la raíz del proyecto RescueTwin-AI.
    Los tests están pensados para ejecutarse desde la raíz del proyecto:

        pytest tests
    """
    return Path(__file__).resolve().parents[1]
