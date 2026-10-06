# Installation

 ```{include} ../README.md
 :start-after: <!-- start-install -->
 :end-before: <!-- end-install -->
 ```

 ## Requirements

 - Python 3.9 or newer
 - For running simulations: a local Talsim engine (`talsimw64.exe`, Windows).

 ## Optional extras

 | Extra | Installs | Required for |
 |---|---|---|
 | `plot` | matplotlib | {meth}`Timeseries.plot() <talsimpy.Timeseries.plot>` |
 | `raster` | xarray, rioxarray | {meth}`TalsimDataset.results_to_xarray() <talsimpy.TalsimDataset.results_to_xarray>` |

 ## Development installation

 ```bash
 git clone https://github.com/sydroconsult/talsimpy.git
 cd talsimpy
 uv sync --group test --group docs
 uv run pytest
 uv run sphinx-build -b html docs docs/_build/html
 ```