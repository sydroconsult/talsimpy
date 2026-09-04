import pytest

from talsimpy import TalsimDatabase, TalsimScenario


def test_open_database_lists_scenarios(talsim_db_path):
    tdb = TalsimDatabase(talsim_db_path)
    assert tdb.scenarios == {1: "Getting started"}


def test_open_scenario_returns_talsimscenario(talsim_db_path):
    tdb = TalsimDatabase(talsim_db_path)
    scenario = tdb.open_scenario(1)
    assert isinstance(scenario, TalsimScenario)
    assert scenario.id == 1
    assert scenario.name == "Getting started"


def test_open_invalid_database_raises(tmp_path):
    # sqlite3 lazily creates the file, so the failure happens when querying
    # the (nonexistent) Scenario table; that error is caught, but the
    # `finally` block then references `result`, which was never assigned -
    # this currently raises UnboundLocalError rather than failing cleanly
    bad_path = tmp_path / "not_a_database.db"
    with pytest.raises(UnboundLocalError):
        TalsimDatabase(bad_path)
