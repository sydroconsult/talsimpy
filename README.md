# talsimpy
 <!-- start-intro -->
Python interface for Talsim datasets, databases, scenarios, simulation runs and time series processing.
<!-- end-intro -->

[Documentation](https://sydroconsult.github.io/talsimpy/)

## Installation
<!-- start-install -->
```bash
pip install talsimpy
```

Optional extras: `pip install talsimpy[plot]` (plotting) or `talsimpy[raster]` (xarray/rioxarray).
<!-- end-install -->

## Features
<!-- start-features -->
* `TalsimDataset` – read and edit Talsim ASCII datasets
* `TalsimDatabase` – interact with a Talsim 5 database
* `TalsimScenario` – manage a scenario within a database
* `TalsimEngine` – run simulations
* `Timeseries` – process time series
<!-- end-features -->

## Example

```python
from talsimpy import TalsimDatabase

db = TalsimDatabase("path/to/database.db")
```
