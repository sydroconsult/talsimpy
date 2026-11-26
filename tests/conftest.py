from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import sys

import pytest

TALSIM_DB_PATH = Path(__file__).parent.parent / "examples" / "data" / "talsim_db" / "Demo.db"
TALSIM_ZRE_DIR = Path(__file__).parent.parent / "examples" / "data" / "talsim_db" / "Demo_zre"
TALSIM_DATASET_DIR = Path(__file__).parent.parent / "examples" / "data" / "test_batch"
TALSIM_DATASET_NAME = "test"
KAL_FAKTOR_DIR = Path(__file__).parent.parent / "examples" / "data" / "test_kal-faktor"
KAL_FAKTOR_NAME = "Test_KAL-Faktor"

# Talsim engine for tests marked with "engine"
ENGINE_PATH_ENV = "TALSIMPY_ENGINE_PATH"
DEFAULT_ENGINE_ROOT = Path(r"C:\Program Files\Talsim\Simulation\engine")
ENGINE_EXE = "talsimw64.exe"


def pytest_addoption(parser):
    parser.addoption(
        "--engine-path",
        default=None,
        help=f"Directory containing {ENGINE_EXE} for engine tests "
             f"(alternatively set {ENGINE_PATH_ENV}, default: newest version in {DEFAULT_ENGINE_ROOT})",
    )


def pytest_configure(config):
    # abort the whole test run right away if an explicitly given engine path is invalid
    _find_engine_dir(config)


def _find_engine_dir(config) -> Path | None:
    """
    Returns the engine directory to use for engine tests or None if no engine is available.

    Order: --engine-path, TALSIMPY_ENGINE_PATH, newest version in DEFAULT_ENGINE_ROOT.
    An explicitly given path that does not contain the engine raises a UsageError.
    """
    for source, value in (("--engine-path", config.getoption("--engine-path")),
                          (ENGINE_PATH_ENV, os.environ.get(ENGINE_PATH_ENV))):
        if value:
            path = Path(value)
            if not (path / ENGINE_EXE).is_file():
                raise pytest.UsageError(f"{source}: {ENGINE_EXE} not found in {path}")
            return path

    if not DEFAULT_ENGINE_ROOT.is_dir():
        return None
    versions = []
    for path in DEFAULT_ENGINE_ROOT.iterdir():
        if re.fullmatch(r"\d+(\.\d+)*", path.name) and (path / ENGINE_EXE).is_file():
            versions.append((tuple(int(x) for x in path.name.split(".")), path))
    if not versions:
        return None
    return max(versions)[1]


@pytest.fixture(scope="session")
def engine_source_dir(pytestconfig):
    """Directory of the locally installed Talsim engine (skips the test if there is none)"""
    if sys.platform != "win32":
        pytest.skip("Talsim engine tests require Windows")
    path = _find_engine_dir(pytestconfig)
    if path is None:
        pytest.skip(f"Talsim engine not found - set {ENGINE_PATH_ENV} or use --engine-path")
    return path


@pytest.fixture
def engine_dir(engine_source_dir, tmp_path):
    """Copy of the Talsim engine in a temporary directory (the engine directory must be writable)"""
    dest = tmp_path / "engine"
    shutil.copytree(engine_source_dir, dest)
    return dest


@pytest.fixture
def talsim_engine(engine_dir):
    from talsimpy import TalsimEngine
    return TalsimEngine(engine_dir)


def _ignore_results(directory, names):
    return [n for n in names
            if n == "results" or Path(n).suffix.upper() in (".MAX", ".WMX", ".BLZ", ".WRN", ".ERR", ".LOG", ".WELINFO", ".WEL", ".WBL")]


@pytest.fixture
def kal_faktor_dir(tmp_path):
    """Copy of the complete example dataset Test_KAL-Faktor (without results)"""
    dest = tmp_path / "kal_faktor"
    shutil.copytree(KAL_FAKTOR_DIR, dest, ignore=_ignore_results)
    return dest


@pytest.fixture
def kal_faktor_dataset(kal_faktor_dir):
    from talsimpy import TalsimDataset
    return TalsimDataset(kal_faktor_dir, KAL_FAKTOR_NAME)


@pytest.fixture
def demo_scenario(talsim_db_copy):
    from talsimpy import TalsimScenario
    return TalsimScenario(talsim_db_copy, 1)


@pytest.fixture
def talsim_zre_dir():
    return TALSIM_ZRE_DIR


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

TEST_DATA_DIR = Path(__file__).parent / "data"
@pytest.fixture
def wel_path():
    return TEST_DATA_DIR / "test.KTR.WEL"