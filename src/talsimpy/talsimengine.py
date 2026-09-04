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
import datetime as dt
import logging
from pathlib import Path
import re
import subprocess

from .talsimdataset import TalsimDataset
from .talsimscenario import TalsimScenario

logger = logging.getLogger(__name__)

FILENAME_EXE = "talsimw64.exe"
FILENAME_CHANGELOG = "TALSIM.CHANGELOG"

class TalsimEngine:
    """
    Class for carrying out simulations with Talsim
    """

    def __init__(self, path: Path|str):
        """
        Instantiate a new TalsimEngine instance

        :param path: path to directory containing the engine executable
        """
        self.path = Path(path)

        # check UNC paths
        if str(self.path.absolute()).startswith("\\"):
            raise Exception(f"Running Talsim from a network path is not supported! Please map the network drive to a local drive letter.")

        # check executable exists
        if not self.exe_file.exists():
            raise Exception(f"Talsim executable {self.exe_file} not found!")

    @property
    def exe_file(self) -> Path:
        """
        Returns the path to the executable
        """
        return self.path / FILENAME_EXE
    
    @property
    def version(self) -> str:
        """
        Returns the Talsim engine version number
        """
        changelog = self.path / FILENAME_CHANGELOG

        if not changelog.exists():
            raise Exception(f"Changelog {changelog} not found!")

        with open(changelog, "r") as f:
            for line in f:
                m = re.match(r"Version (\d+\.\d+\.\d+(.+)?)", line)
                if m:
                    return m.group(1)
            else:
                raise Exception("Unable to read version number from changelog")


    def simulate(self, 
                 dataset: TalsimDataset|TalsimScenario, 
                 name: str = None,
                 variation_id: int = 0, 
                 language: str = "de", 
                 path_timeseries: Path|str = None,
                 sim_id: int = None,
                 path_output: Path|str = None,
                 ) -> bool:
        """
        Carries out a simulation
        
        :param dataset: TalsimDataset or TalsimScenario instance to simulate
        :param name: optional name for the output files (only relevant for TalsimScenario instances, defaults to scenario name)
        :param variation_id: optional Variation ID (default: 0)
        :param language: optional language (default: "de")
        :param path_timeseries: optional path to time series files (only relevant for TalsimScenario instances)
        :param sim_id: optional simulation id (only relevant for TalsimScenario instances, defaults to active simulation id)
        :param path_output: optional output path (only relevant for TalsimScenario instances)
        :return: boolean success
        """

        # check
        if isinstance(dataset, TalsimScenario):
            if int(self.version.split(".")[0]) < 4:
                raise Exception(f"Simulating a TalsimScenario instance requires Talsim.Engine >= 4.x!")
            if path_timeseries is None:
                raise Exception(f"Parameter path_timeseries not provided!")
            path_timeseries = Path(path_timeseries)
            if not path_timeseries.exists():
                raise Exception(f"Path to timeseries {path_timeseries} not found!")
            if sim_id is None:
                if dataset.sim_id is None:
                    raise Exception(f"Parameter sim_id not provided and active simulation id is not set!")
                else:
                    logger.info(f"No simulation id provided, using active simulation id {dataset.sim_id} from scenario.")
                    sim_id = dataset.sim_id
            if path_output is None:
                raise Exception(f"Parameter path_output not provided!")
            path_output = Path(path_output)
            if not path_output.exists():
                raise Exception(f"Output path {path_output} not found!")
            
        # system_name has multipe purposes:
        # * for TalsimDataset (ASCII), it is used both for specifying the input filenames and for naming the output files
        # * for TalsimScenario (database), it is used only for naming the output files
        if isinstance(dataset, TalsimScenario):
            if name is not None:
                system_name = name
            else:
                # if no name is provided, use scenario name
                #TODO: the scenario name as defined in the database may not always be suitable as a filename template!
                system_name = dataset.name
        else:
            system_name = dataset.name

        # prepare runfile
        runfile = self.path / "talsim.run"
        with open(runfile, "w") as f:
            f.write("[TALSIM]\n")
            if isinstance(dataset, TalsimScenario):
                f.write(f"Path={path_output.resolve()}\\\n")
            else:
                f.write(f"Path={dataset.path.resolve()}\\\n")
            f.write(f"System={system_name}\n")
            if isinstance(dataset, TalsimScenario):
                f.write(f"DBFile={dataset.db.resolve()}\n")
                f.write(f"ZrePath={path_timeseries.resolve()}\\\n")
                f.write(f"ScenarioId={dataset.id}\n")
                f.write(f"SimulationId={sim_id}\n")
            f.write("ExecMode=0\n")
            f.write(f"VariationId={variation_id}\n")
            f.write(f"Language={language}\n")

        # launch talsim
        retcode = self.launch(runfile)

        # if it is a database scenario, update DateSimulated and reset HasResults, ErrorMessage
        if isinstance(dataset, TalsimScenario):
            dataset.set_parameter(table="Simulation", id=sim_id, field="DateSimulated", value=f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}")
            dataset.set_parameter(table="Simulation", id=sim_id, field="HasResults", value=0)
            dataset.set_parameter(table="Simulation", id=sim_id, field="ErrorMessage", value=None)

        # check for warnings file
        file_wrn = dataset.path / f"{system_name}.wrn"
        if file_wrn.exists():
            logger.warning(f"Simulation produced warnings! See Talsim warning file: {file_wrn}")

        if retcode != 0:
            # simulation error
            # check for error file
            file_err = dataset.path / f"{system_name}.err"
            if file_err.exists():
                logger.error(f"Simulation ended with errors! See Talsim error file: {file_err}")
                # if it is a database scenario, update ErrorMessage
                if isinstance(dataset, TalsimScenario):
                    dataset.set_parameter(table="Simulation", id=sim_id, field="ErrorMessage", value=dataset.errors)
            else:
                logger.error(f"Simulation aborted without error message!")
            return False
        else:
            # simulation successful
            logger.info("Simulation successful!")
            # if it is a database scenario, update HasResults and LastSuccessEngineVersion
            if isinstance(dataset, TalsimScenario):
                dataset.set_parameter(table="Simulation", id=sim_id, field="HasResults", value=1)
                dataset.set_parameter(table="Simulation", id=sim_id, field="LastSuccessEngineVersion", value=self.version)
            return True


    def launch(self, runfile: Path|str) -> int:
        """
        Launches the Talsim engine with a given run file

        :param runfile: path to run file
        :return: return code of the process
        """
        runfile = Path(runfile)
        if not runfile.exists():
            raise Exception(f"Run file {runfile} not found!")
        
        if runfile.parent.absolute() == self.path.absolute():
            # if the runfile is in the same directory as the engine, we can just pass the filename to avoid issues with long paths
            runfile = runfile.name
        else:
            runfile = runfile.absolute()
            if "-" in str(runfile):
                #TODO: cannot deal with run file paths containing hyphens due to a bug in the Talsim engine (see #457).
                raise Exception(f"Run file path {runfile} contains a hyphen, which is currently not supported by Talsim engine (see #457)!")

        logger.info(f"Launching Talsim-NG v{self.version}...")
        
        args = [self.exe_file.name, runfile]
        logger.debug(f"Running command: {' '.join(map(str, args))} in {self.path.absolute()}")
        proc = subprocess.Popen(args, cwd=self.path.absolute(), shell=True)
        retcode = proc.wait()

        return retcode

    def ktrcheck(self, 
                 dataset: TalsimDataset|TalsimScenario, 
                 language: str = "de", 
                 path_output = None,
                 ) -> bool:
        """
        Carries out a KTRCheck run

        :param dataset: TalsimDataset or TalsimScenario instance to check
        :param language: optional language (default: "de")
        :param path_output: optional output path (only relevant for TalsimScenario instances)
        :return: boolean success
        """
        # checks

        # get version number parts
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.+)?$", self.version)
        if not m:
            raise Exception(f"Unable to parse version number {self.version}!")
        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        
        # check whether version is >= 4.1.17 (the version where KTRCheck was introduced)
        if major < 4 or minor < 1 or patch < 17:
            raise Exception(f"Running a KTRCheck requires Talsim.Engine >= 4.1.17!")
        
        if isinstance(dataset, TalsimScenario):
            if major < 4:
                raise Exception(f"Handling a TalsimScenario instance requires Talsim.Engine >= 4.x!")
            if path_output is None:
                raise Exception(f"Parameter path_output not provided!")
            path_output = Path(path_output)
            if not path_output.exists():
                raise Exception(f"Output path {path_output} not found!")

        # prepare runfile
        runfile = self.path / "talsim.run"
        with open(runfile, "w") as f:
            f.write("[TALSIM]\n")
            if isinstance(dataset, TalsimScenario):
                f.write(f"Path={path_output.resolve()}\\\n")
            else:
                f.write(f"Path={dataset.path.resolve()}\\\n")
            f.write(f"System={dataset.name}\n") #TODO: the scenario name may not always be suitable as a filename template!
            if isinstance(dataset, TalsimScenario):
                f.write(f"DBFile={dataset.db.resolve()}\n")
                f.write(f"ZrePath=\n")
                f.write(f"ScenarioId={dataset.id}\n")
                f.write(f"SimulationId={dataset.sim_id}\n")
            f.write("ExecMode=0\n")
            f.write(f"VariationId=0\n")
            f.write(f"Language={language}\n")

        # run talsim
        logger.info(f"Launching Talsim-NG v{self.version}...")

        args = [self.exe_file.resolve(), runfile.name, "-ktrcheck"]
        proc = subprocess.Popen(args, cwd=self.path.resolve())
        retcode = proc.wait()

        if retcode != 0:
            # error
            # check for error file
            file_err = dataset.path / f"{dataset.name}.err"
            if file_err.exists():
                logger.error(f"KTRCheck ended with errors! See Talsim error file: {file_err}")
            else:
                logger.error(f"KTRCheck aborted without error message!")
            return False
        else:
            # success
            logger.info("KTRCheck successful!")
            return True


    def __repr__(self) -> str:
        return f"TalsimEngine in {self.path}"


    @staticmethod
    def read_runfile(runfile: Path|str) -> dict[str, str]:
        """
        Reads a run file and returns the settings as a dictionary
        
        :param runfile: path to run file
        :return: dictionary with settings
        """
        # read run file
        runsettings = {}
        with open(runfile, "r") as f:
            for line in f:
                if line.strip().startswith("#"):
                    # skip comments
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    runsettings[key] = value

        return runsettings