import datetime

import pytest

from talsimpy import TalsimDatabase, TalsimScenario


def open_scenario(db_path):
    return TalsimDatabase(db_path).open_scenario(1)


def test_scenario_metadata(talsim_db_copy):
    scenario = open_scenario(talsim_db_copy)
    assert scenario.simulations
    assert scenario.active_simulation in scenario.simulations


def test_set_active_simulation(talsim_db_copy):
    scenario = open_scenario(talsim_db_copy)
    sim_id = next(iter(scenario.simulations))

    scenario.set_active_simulation(sim_id)
    assert scenario.active_simulation == sim_id

    # persisted: a freshly opened scenario reflects the change too
    reopened = open_scenario(talsim_db_copy)
    assert reopened.active_simulation == sim_id


def test_set_active_simulation_invalid_id_raises(talsim_db_copy):
    scenario = open_scenario(talsim_db_copy)
    with pytest.raises(Exception):
        scenario.set_active_simulation(999999)


def test_sim_start_and_end_roundtrip(talsim_db_copy):
    scenario = open_scenario(talsim_db_copy)

    new_start = datetime.datetime(2010, 1, 1)
    new_end = datetime.datetime(2010, 12, 31)
    scenario.set_sim_start(new_start)
    scenario.set_sim_end(new_end)

    assert scenario.sim_start == new_start
    assert scenario.sim_end == new_end

    # persisted: a freshly opened scenario reflects the change too
    reopened = open_scenario(talsim_db_copy)
    assert reopened.sim_start == new_start
    assert reopened.sim_end == new_end


def test_set_parameter(talsim_db_copy):
    scenario = open_scenario(talsim_db_copy)
    sim_id = scenario.active_simulation

    scenario.set_parameter(table="Simulation", id=sim_id, field="Description", value="Test run")

    reopened = open_scenario(talsim_db_copy)
    assert reopened.simulations[sim_id] == "Test run"


def test_copy_is_independent_from_original(talsim_db_copy, tmp_path):
    scenario = open_scenario(talsim_db_copy)
    destination = tmp_path / "copy"

    scenario_copy = scenario.copy(destination)

    assert isinstance(scenario_copy, TalsimScenario)
    assert scenario_copy.db == destination / talsim_db_copy.name
    assert scenario_copy.db.exists()

    # modifying the copy does not affect the original
    scenario_copy.set_sim_start(datetime.datetime(1999, 1, 1))
    original_reopened = open_scenario(talsim_db_copy)
    assert original_reopened.sim_start != datetime.datetime(1999, 1, 1)
