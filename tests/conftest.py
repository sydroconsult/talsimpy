from pathlib import Path
import shutil

import pytest

TALSIM_DB_PATH = Path(__file__).parent.parent / "examples" / "data" / "talsim_db" / "Demo.db"
TALSIM_DATASET_DIR = Path(__file__).parent.parent / "examples" / "data" / "test_batch"
TALSIM_DATASET_NAME = "test"


@pytest.fixture
def talsim_db_path():
    return TALSIM_DB_PATH


@pytest.fixture
def talsim_db_copy(tmp_path):
    dest = tmp_path / "Demo.db"
    shutil.copy2(TALSIM_DB_PATH, dest)
    return dest


@pytest.fixture
def talsim_dataset_path():
    return TALSIM_DATASET_DIR, TALSIM_DATASET_NAME


@pytest.fixture
def talsim_dataset_copy(tmp_path):
    dest = tmp_path / "dataset"
    shutil.copytree(TALSIM_DATASET_DIR, dest)
    return dest, TALSIM_DATASET_NAME
