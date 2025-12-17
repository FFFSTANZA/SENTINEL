# pytest_plugins is not needed when using entry_points in pyproject.toml

import os
import pytest


@pytest.fixture(autouse=True)
def preserve_cwd():
    """Preserve current working directory across tests"""
    cwd = os.getcwd()
    yield
    try:
        os.chdir(cwd)
    except (FileNotFoundError, OSError):
        # If original directory was deleted, change to a safe location
        os.chdir("/home/engine/project")
