# -*- coding: utf-8 -*-
# ---------------------------------------------------------
# Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
# This file may not be copied, modified and/or distributed
# without the express permission of SYDRO Consult GmbH
# ---------------------------------------------------------
"""
Package talsim
"""
from __future__ import annotations
import logging
from pathlib import Path
import sqlite3

from .talsimscenario import TalsimScenario

logger = logging.getLogger(__name__)

class TalsimDatabase():
    """
    CLass for handling a Talsim 5 database
    """

    def __init__(self, path: Path|str):

        self.path = Path(path)
        self.scenarios: dict[int, str] = {} # {id: name, ...}

        try:
            conn = sqlite3.Connection(path)
            # read scenarios
            result = conn.execute("SELECT Id, Name FROM Scenario ORDER BY Id;")
            for id, name in result:
                self.scenarios[id] = name

        except Exception as e:
            logger.error(f"Error while reading Talsim database: {e}")

        finally:
            result.close()
            conn.close()


    def open_scenario(self, scenario_id: int) -> TalsimScenario:
        """
        Opens a scenario from the database, returning a corresponding TalsimScenario instance
        """
        return TalsimScenario(self.path, scenario_id)
    
    
    def __repr__(self) -> str:
        return f"Talsim database at {self.path}"