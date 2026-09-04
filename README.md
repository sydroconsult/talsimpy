# talsimpy

Python interface for Talsim datasets, databases, scenarios, simulation runs and time series processing.

## Installation

```bash
pip install talsimpy
```

Optional extras: `pip install talsimpy[plot]` (plotting) or `talsimpy[raster]` (xarray/rioxarray).

## Features

* `TalsimDataset` – read and edit Talsim ASCII datasets
* `TalsimDatabase` – interact with a Talsim 5 database
* `TalsimScenario` – manage a scenario within a database
* `TalsimEngine` – run simulations
* `Timeseries` – process time series

## Example

```python
from talsimpy import TalsimDatabase

db = TalsimDatabase("path/to/database.db")
```
