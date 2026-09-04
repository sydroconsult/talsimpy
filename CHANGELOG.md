# talsim package

Version 3.0.0a1
----------------
CHANGED:
* Package renamed from `pytalsim` to `talsimpy` (the `pytalsim` name is no longer available on PyPI); import as `import talsimpy` instead of `import pytalsim`
* First release under the new name, published as an alpha to reflect that the accompanying test suite and example notebooks are still being ported over

Version 2.1.3
-------------
FIXED:
* Fix error handling when trying to open a nonexistant scenario

Version 2.1.2
-------------
FIXED:
* Improved handling of different combinations of engine path and run file, disallow using UNC paths as the location of the engine

Version 2.1.1
-------------
FIXED:
* Fixed `TalsimEngine.simulate()` not using the passed `sim_id` argument as the simulation id (was using the active simulation id as set in the database instead)

Version 2.1.0
-------------
NEW:
* New static method `TalsimEngine.launch()` for launching a simulation using an existing run file
* New static method `TalsimEngine.read_runfile()` for reading a run file
* `TalsimEngine.simulate()` now has an additional optional parameter `name` for specifying the output filenames (only relevant for TalsimScenario instances)

FIXED:
* Fixed `TalsimDataset.file_to_dataframe()` not working for EFL version 1.2 files

REMOVED:
* Removed method `TalsimScenario.copy_simulation()` because it doesn't deal with calibrations and calibration mapping which would need to be copied/adjusted as well
