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

 ## Tests with the Talsim engine

 Tests marked with `engine` (`tests/test_talsimengine.py`) run real simulations. They are optional:
 if no engine is found, they are skipped. The engine is searched in this order:

 1. pytest option `--engine-path=<dir>` (note the `=`)
 2. environment variable `TALSIMPY_ENGINE_PATH`
 3. the newest version in `C:\Program Files\Talsim\Simulation\engine\`

 An explicitly given path that does not contain `talsimw64.exe` aborts the test run.
 The engine is copied to a temporary directory for each test, so the installation itself is not modified.

 ```powershell
 uv run pytest -rs                     # all tests, -rs shows why tests were skipped
 uv run pytest -m engine               # only engine tests
 uv run pytest -m "not engine"         # without engine tests
 uv run pytest "--engine-path=D:\Talsim\engine\4.1.28"
 $env:TALSIMPY_ENGINE_PATH = "D:\Talsim\engine\4.1.28"     # current session
 setx TALSIMPY_ENGINE_PATH "D:\Talsim\engine\4.1.28"       # permanently (new shell required)
 ```