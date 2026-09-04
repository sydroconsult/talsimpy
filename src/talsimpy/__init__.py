# -*- coding: utf-8 -*-
# ---------------------------------------------------------
# Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
# This file may not be copied, modified and/or distributed
# without the express permission of SYDRO Consult GmbH
# ---------------------------------------------------------
"""
Package talsim

This package contains the following classes:
* `TalsimDataset` for handling and manipulating a Talsim ASCII dataset
* `TalsimDatabase` for handling a Talsim 5 database
* `TalsimScenario` for handling and manipulating a scenario in a database
* `TalsimEngine` for carrying out simulations with Talsim
* `Timeseries` for handling and manipulating time series
"""

__version__ = "3.0.0a1"

from .talsimdatabase import TalsimDatabase
from .talsimdataset import TalsimDataset
from .talsimscenario import TalsimScenario
from .talsimengine import TalsimEngine
from .timeseries import Timeseries
