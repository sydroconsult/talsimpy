# Quickstart

This guide shows a typical workflow with a Talsim 5 database: open a scenario,
adjust the simulation, run it and read the results.

## Open a database

```python
import datetime as dt
from talsimpy import TalsimDatabase, TalsimEngine, Timeseries

db = TalsimDatabase("data/talsim_db/Demo.db")

# list all scenarios {id: name}
print(db.scenarios)
```

## Open a scenario

```python
scenario = db.open_scenario(1)

# simulations defined for this scenario {id: name}
print(scenario.simulations)

# check and set the active simulation
print(scenario.active_simulation)
scenario.set_active_simulation(1)

print(scenario.sim_start, scenario.sim_end)
```

## Work on a copy

To keep the original database unchanged, copy the scenario (i.e. the whole database)
to a working directory first:

```python
scenario = scenario.copy("tmp")
```

## Modify the simulation

```python
scenario.set_sim_start(dt.datetime(2020, 7, 1))
scenario.set_sim_end(dt.datetime(2020, 12, 31))

# any other value can be changed with the generic method
scenario.set_parameter(table="Simulation", id=1, field="StartKey", value="T001")
```

## Run the simulation

```python
engine = TalsimEngine(r"C:\path\to\talsim_engine")
print(engine.version)

success = engine.simulate(
    scenario,
    name="demo",
    path_timeseries="data/talsim_db/Demo_zre",
    path_output=scenario.path,
)
if not success:
    print(scenario.errors)
```


## Read the results

```python
print(scenario.warnings)

# list of WEL/WBL result files
files = scenario.timeseries_result_files
print(files)

# read a single series and plot it (requires the "plot" extra)
ts, = Timeseries.read_wel(files[0], ["T001_VOL"])
ts.plot()
```

## Next steps

- {doc}`api` – full reference of all classes and methods
- [talsim5.ipynb](https://github.com/sydroconsult/talsimpy/blob/main/examples/talsim5.ipynb) – the complete example notebook
