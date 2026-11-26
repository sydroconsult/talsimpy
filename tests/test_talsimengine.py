"""
Tests that run the real Talsim engine.

They are skipped if no engine is found. The engine is searched in this order:
``--engine-path``, environment variable ``TALSIMPY_ENGINE_PATH``,
newest version in ``C:\\Program Files\\Talsim\\Simulation\\engine`` (see conftest.py).
"""
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from talsimpy import TalsimDataset, TalsimEngine

pytestmark = pytest.mark.engine

PATH_KINDS = ["relative", "absolute"]


def _engine(engine_dir: Path, path_kind: str, monkeypatch) -> TalsimEngine:
    """Returns a TalsimEngine instance created with a relative or absolute path"""
    if path_kind == "relative":
        monkeypatch.chdir(engine_dir.parent)
        return TalsimEngine(engine_dir.name)
    return TalsimEngine(engine_dir.resolve())


def _assert_simulation_successful(dataset: TalsimDataset):
    path = Path(dataset.path)
    assert not (path / f"{dataset.name}.err").exists(), (path / f"{dataset.name}.err").read_text(errors="replace")
    file_wel = path / f"{dataset.name}.WEL"
    assert file_wel.exists()
    assert file_wel.stat().st_size > 0


def _read_simulation(db: Path, sim_id: int) -> tuple:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT HasResults, LastSuccessEngineVersion FROM Simulation WHERE Id = ?;", (sim_id,)
        ).fetchone()
    finally:
        conn.close()


# --- basics ---

def test_engine_version(talsim_engine):
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", talsim_engine.version)


def test_simulate_dataset_success(talsim_engine, kal_faktor_dataset):
    assert talsim_engine.simulate(kal_faktor_dataset) is True
    _assert_simulation_successful(kal_faktor_dataset)


def test_simulate_dataset_error(talsim_engine, talsim_dataset_copy):
    # test_batch has no *.EXT file (only a template), so the engine aborts with an error file
    path, name = talsim_dataset_copy
    dataset = TalsimDataset(path, name)
    assert talsim_engine.simulate(dataset) is False
    assert (path / f"{name}.err").exists()


def test_simulate_scenario_success(talsim_engine, demo_scenario, talsim_zre_dir, tmp_path):
    path_output = tmp_path / "output"
    path_output.mkdir()
    result = talsim_engine.simulate(demo_scenario, name="demo",
                                    path_timeseries=talsim_zre_dir, path_output=path_output)
    assert result is True
    has_results, engine_version = _read_simulation(demo_scenario.db, demo_scenario.sim_id)
    assert has_results == 1
    assert engine_version == talsim_engine.version


# --- relative and absolute paths ---

@pytest.mark.parametrize("path_kind", PATH_KINDS)
def test_simulate_engine_path(engine_dir, kal_faktor_dataset, path_kind, monkeypatch):
    engine = _engine(engine_dir, path_kind, monkeypatch)
    assert engine.simulate(kal_faktor_dataset) is True
    _assert_simulation_successful(kal_faktor_dataset)


@pytest.mark.parametrize("path_kind", PATH_KINDS)
def test_simulate_dataset_path(talsim_engine, kal_faktor_dir, path_kind, monkeypatch):
    from conftest import KAL_FAKTOR_NAME
    if path_kind == "relative":
        monkeypatch.chdir(kal_faktor_dir.parent)
        dataset = TalsimDataset(kal_faktor_dir.name, KAL_FAKTOR_NAME)
    else:
        dataset = TalsimDataset(kal_faktor_dir.resolve(), KAL_FAKTOR_NAME)
    assert talsim_engine.simulate(dataset) is True
    _assert_simulation_successful(dataset)


@pytest.mark.parametrize("path_kind", PATH_KINDS)
def test_launch_runfile_in_engine_dir(talsim_engine, kal_faktor_dataset, path_kind, monkeypatch):
    # simulate() writes talsim.run to the engine directory, which is then launched again
    assert talsim_engine.simulate(kal_faktor_dataset) is True
    runfile = talsim_engine.path / "talsim.run"
    if path_kind == "relative":
        monkeypatch.chdir(talsim_engine.path)
        runfile = Path(runfile.name)
    else:
        runfile = runfile.resolve()
    assert talsim_engine.launch(runfile) == 0


def test_launch_runfile_outside_engine_dir(talsim_engine, kal_faktor_dataset):
    assert talsim_engine.simulate(kal_faktor_dataset) is True
    dir_run = Path(tempfile.mkdtemp())
    try:
        if "-" in str(dir_run):
            pytest.skip(f"Temp directory {dir_run} contains a hyphen")
        runfile = dir_run / "talsim.run"
        shutil.copy2(talsim_engine.path / "talsim.run", runfile)
        assert talsim_engine.launch(runfile) == 0
    finally:
        shutil.rmtree(dir_run, ignore_errors=True)


def test_launch_runfile_with_hyphen_raises(talsim_engine, kal_faktor_dataset, tmp_path):
    # tmp_path always contains "pytest-of-<user>", hyphens are not supported by the engine (see #457)
    assert talsim_engine.simulate(kal_faktor_dataset) is True
    runfile = tmp_path / "run" / "talsim.run"
    runfile.parent.mkdir()
    shutil.copy2(talsim_engine.path / "talsim.run", runfile)
    assert "-" in str(runfile.absolute())
    with pytest.raises(Exception, match="hyphen"):
        talsim_engine.launch(runfile)


# --- regression test for #13 ---

@pytest.mark.parametrize("env_value", [None, "1"])
@pytest.mark.parametrize("path_kind", PATH_KINDS)
def test_simulate_no_default_current_directory_in_exe_path(engine_dir, kal_faktor_dataset, path_kind, env_value, monkeypatch):
    if env_value is None:
        monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)
    else:
        monkeypatch.setenv("NoDefaultCurrentDirectoryInExePath", env_value)
    engine = _engine(engine_dir, path_kind, monkeypatch)
    assert engine.simulate(kal_faktor_dataset) is True
    _assert_simulation_successful(kal_faktor_dataset)
