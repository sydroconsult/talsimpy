import datetime

import pytest

from talsimpy import TalsimDataset, Timeseries


def open_dataset(dataset_path_and_name):
    path, name = dataset_path_and_name
    return TalsimDataset(path, name)


def test_open_dataset(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    assert ds.name == "test"
    assert ds.path.exists()


def test_open_dataset_nonexistent_path_raises(tmp_path):
    with pytest.raises(ValueError):
        TalsimDataset(tmp_path / "does_not_exist", "test")


def test_open_dataset_missing_sys_raises(talsim_dataset_path):
    path, _ = talsim_dataset_path
    with pytest.raises(ValueError):
        TalsimDataset(path, "wrong_name")


def test_sim_start_and_end(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    assert ds.sim_start == datetime.datetime(2020, 11, 2)
    assert ds.sim_end == datetime.datetime(2021, 7, 30)


def test_get_sim_options(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    options = ds.get_sim_options()
    assert options["SimStart"] == "02.11.2020 00:00"
    assert options["SimEnd"] == "30.07.2021 00:00"
    assert options["TimeStep_min"] == "60"


def test_set_sim_options_updates_all_file(talsim_dataset_copy):
    ds = TalsimDataset(*talsim_dataset_copy)
    ds.set_sim_options({"SimStart": datetime.datetime(2020, 1, 1), "NonexistentOption": 123})

    reopened = TalsimDataset(*talsim_dataset_copy)
    assert reopened.get_sim_options()["SimStart"] == "01.01.2020 00:00"


def test_set_calibration_parameters(talsim_dataset_copy):
    ds = TalsimDataset(*talsim_dataset_copy)
    ds.set_calibration_parameters({"RetKonFakNat": 5})

    path, name = talsim_dataset_copy
    kal_content = (path / f"{name}.KAL").read_text(encoding="cp1252")
    assert "RetKonFakNat=5" in kal_content


def test_file_to_dataframe_boa(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    df = ds.file_to_dataframe("BOA")
    assert len(df) == 10
    assert df.iloc[0]["Bemerkkung"] == "Boden_1"


def test_file_to_dataframe_bod(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    df = ds.file_to_dataframe("BOD")
    assert len(df) == 10
    assert df.iloc[0]["Bemerkung"] == "Profil_1"


def test_file_to_dataframe_efl(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    df = ds.file_to_dataframe("EFL")
    assert len(df) == 12
    assert set(df["EZG"]) == {"AB23"}


def test_file_to_dataframe_ezg(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    df = ds.file_to_dataframe("EZG")
    assert len(df) == 1
    assert df.iloc[0]["Bez"] == "AB23"


def test_calculate_average_soil_properties(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    df = ds.calculate_average_soil_properties()
    assert len(df) == 10
    assert set(df.columns) == {"Bod_ID", "WP_Average", "FK_Average", "GPV_Average"}


def test_copy_creates_independent_dataset(talsim_dataset_path, tmp_path):
    ds = open_dataset(talsim_dataset_path)
    destination = tmp_path / "copy"

    ds_copy = ds.copy(destination)

    assert isinstance(ds_copy, TalsimDataset)
    assert ds_copy.path == destination
    assert (destination / f"{ds.name}.SYS").exists()

    # modifying the copy does not affect the original
    ds_copy.set_sim_options({"SimStart": datetime.datetime(1999, 1, 1)})
    assert ds.get_sim_options()["SimStart"] != "01.01.1999 00:00"


def test_timeseries_result_files_empty_when_no_results(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    assert ds.timeseries_result_files == []


def test_warnings_and_errors_are_none_when_absent(talsim_dataset_path):
    ds = open_dataset(talsim_dataset_path)
    assert ds.warnings is None
    assert ds.errors is None


def test_write_varfile(talsim_dataset_copy):
    ds = TalsimDataset(*talsim_dataset_copy)
    ts = Timeseries(title="test")
    ts.add_node(datetime.datetime(2020, 1, 1), 1.0)
    ts.add_node(datetime.datetime(2020, 2, 1), 2.0)

    ds.write_varfile("test.var", {"MyParam": ts, "MyFlag": True})

    path, _ = talsim_dataset_copy
    content = (path / "test.var").read_text(encoding="utf-8")
    assert "MyParam" in content
    assert "MyFlag" in content


def test_process_templates(talsim_dataset_copy):
    ds = TalsimDataset(*talsim_dataset_copy)
    fictitious_path = r"C:\example_data\Talsim\test_batch\timeseries\sce_01"

    ds.process_templates({"timeseries_path": fictitious_path})

    path, name = talsim_dataset_copy
    ext_content = (path / f"{name}.EXT").read_text(encoding="cp1252")
    assert fictitious_path in ext_content
    assert "{timeseries_path}" not in ext_content
