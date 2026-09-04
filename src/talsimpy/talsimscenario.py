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
import datetime
import logging
from pathlib import Path
import re
import shutil
import sqlite3

from .talsimdataset import TalsimDataset

logger = logging.getLogger(__name__)

class TalsimScenario(TalsimDataset):
    """
    Class for handling and manipulating a scenario in a database
    """

    db = None
    """Path to the database file"""

    id = None
    """Scenario id"""

    sim_id = None
    """Currently active simulation id"""

    simulations = {}
    """Dictionary of existing simulations {id: name, ...}"""


    def __init__(self, path: Path|str, scenario_id: int):
        """
        Instantiates a new TalsimScenario instance

        :param path: path to database containing the scenario
        :param scenario_id: scenario id
        """
        path = Path(path)

        # check parameters
        if not path.exists():
            raise ValueError(f"Path {path} not found!")
        if not path.suffix.lower() == ".db":
            raise ValueError(f"Path {path} is not a path to a *.db file!")

        try:
            conn = sqlite3.Connection(path)
            # read scenario name and active simulation id
            result = conn.execute("SELECT Name, ActiveSimulationId FROM Scenario WHERE Id = ?;", (scenario_id,))
            row = result.fetchone()
            if row is None:
                raise Exception(f"Scenario with Id {scenario_id} not found in database!")
            name, sim_id = row

        except Exception as e:
            logger.error(f"Error while reading Talsim database: {e}")

        finally:
            result.close()
            conn.close()

        # store data
        self.path = path.parent
        self.name = name
        self.db = path
        self.id = scenario_id
        self.sim_id = sim_id

        # read simulations
        self._get_simulations()


    def _get_simulations(self) -> None:
        """
        Reads all stored simulations from the database and stores the info in `self.simulations`
        """
        try:
            conn = sqlite3.Connection(self.db)
            # read simulations
            self.simulations.clear()
            result = conn.execute("SELECT Id, Description FROM Simulation WHERE ScenarioId = ?;", (self.id,))
            for sim_id, sim_description in result:
                self.simulations[sim_id] = sim_description
        except Exception as e:
            logger.error(f"Error while reading Talsim database: {e}")
        finally:
            result.close()
            conn.close()

        return


    @property
    def active_simulation(self) -> int|None:
        """
        Returns the currently active simulation

        :return: active simulation id or None if not set
        """
        return self.sim_id


    def set_active_simulation(self, sim_id: int) -> None:
        """
        Sets the active simulation id

        :param sim_id: the simulation id to set
        """
        if sim_id not in self.simulations.keys():
            raise Exception(f"Unable to set active simulation id: simulation id {sim_id} does not exist!")
        
        try:
            conn = sqlite3.Connection(self.db)
            # set active simulation id
            result = conn.execute("UPDATE Scenario SET ActiveSimulationId = ? WHERE Id = ?;", (sim_id, self.id))
            if result.rowcount != 1:
                raise Exception(f"Unable to set active simulation id!")
            conn.commit()
            # update stored simulation id
            self.sim_id = sim_id

        except Exception as e:
            logger.error(f"Error while updating Talsim database: {e}")

        finally:
            result.close()
            conn.close()
        
        return
    

    def copy(self, destination: Path|str, include_results: bool = False) -> TalsimScenario:
        """
        Copies the scenario (i.e. the whole database) to a destination directory, optionally including result files

        :param destination: destination directory
        :param include_results: if True, also copy result files (default: False)
        :return: the destination scenario
        """
        destination = Path(destination)

        if not destination.exists():
            destination.mkdir(parents=True)
            
        # collect scenario files
        files = []
        files.append(self.db)
        for file in self.path.glob(f"{self.name}.*"):
            if not include_results and file.suffix.upper() in TalsimDataset.RESULT_EXTENSIONS:
                # omit result files if not requested
                continue
            files.append(file)
        # add any *.var files (can have arbitrary filenames!)
        files.extend(self.path.glob("*.var"))

        # copy files
        for file in files:
            shutil.copy2(file, destination / file.name)

        return TalsimScenario(destination / self.db.name, self.id)


    @property
    def sim_start(self) -> datetime.datetime:
        """
        Returns the simulation start date of the currently active simulation
        """
        if self.sim_id is None:
            raise Exception("Active simulation id is not set!")

        try:
            conn = sqlite3.Connection(self.db)
            # read simulation start date
            result = conn.execute("SELECT SimulationStart FROM Simulation WHERE Id = ?;", (self.sim_id,))
            if result is None:
                raise Exception(f"Simulation with Id {self.sim_id} not found in database!")
            simstart, = result.fetchone()
            simstart = datetime.datetime.strptime(simstart, "%Y-%m-%d %H:%M:%S")

        except Exception as e:
            logger.error(f"Error while reading Talsim database: {e}")

        finally:
            result.close()
            conn.close()

        return simstart


    def set_sim_start(self, sim_start: datetime.datetime) -> None:
        """
        Sets the simulation start date for the currently active simulation
        """
        try:
            conn = sqlite3.Connection(self.db)
            # set simulation start date
            result = conn.execute("UPDATE Simulation SET SimulationStart = ? WHERE Id = ?;", (f"{sim_start:%Y-%m-%d %H:%M:%S}", self.sim_id))
            if result.rowcount != 1:
                raise Exception(f"Unable to set simulation start date for simulation with Id {self.sim_id}!")
            conn.commit()

        except Exception as e:
            logger.error(f"Error while updating Talsim database: {e}")

        finally:
            result.close()
            conn.close()

        return


    @property
    def sim_end(self) -> datetime.datetime:
        """
        Returns the simulation end date for the currently active simulation
        """
        if self.sim_id is None:
            raise Exception("Active simulation id is not set!")

        try:
            conn = sqlite3.Connection(self.db)
            # read simulation end date
            result = conn.execute("SELECT SimulationEnd FROM Simulation WHERE Id = ?;", (self.sim_id,))
            if result is None:
                raise Exception(f"Simulation with Id {self.sim_id} not found in database!")
            simend, = result.fetchone()
            simend = datetime.datetime.strptime(simend, "%Y-%m-%d %H:%M:%S")

        except Exception as e:
            logger.error(f"Error while reading Talsim database: {e}")

        finally:
            result.close()
            conn.close()

        return simend


    def set_sim_end(self, sim_end: datetime.datetime) -> None:
        """
        Sets the simulation end date for the currently active simulation
        """
        try:
            conn = sqlite3.Connection(self.db)
            # set simulation end date
            result = conn.execute("UPDATE Simulation SET SimulationEnd = ? WHERE Id = ?;", (f"{sim_end:%Y-%m-%d %H:%M:%S}", self.sim_id))
            if result.rowcount != 1:
                raise Exception(f"Unable to set simulation end date for simulation with Id {self.sim_id}!")
            conn.commit()

        except Exception as e:
            logger.error(f"Error while updating Talsim database: {e}")

        finally:
            result.close()
            conn.close()

        return


    def set_parameter(self, table: str, id: int, field: str, value: int|float|str) -> None:
        """
        Sets an arbitray value in the database

        :param table: name of the database table
        :param id: Id of the row
        :param field: name of the field
        :param value: new value to set
        """
        try:
            conn = sqlite3.Connection(self.db)
            # update database
            sql = f"UPDATE {table} SET {field} = ? WHERE Id = ?;"
            result = conn.execute(sql, (value, id))
            if result.rowcount != 1:
                raise Exception(f"Database update query affected {result.rowcount} rows! Query: {sql} with value {value} and id {id}")
            conn.commit()

        except Exception as e:
            logger.error(f"Error while updating Talsim database: {e}")

        finally:
            result.close()
            conn.close()

        return


    def __repr__(self) -> str:
        return f"TalsimScenario '{self.name}' with ScenarioId {self.id} in {self.db}"
