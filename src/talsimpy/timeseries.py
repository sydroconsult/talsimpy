# -*- coding: utf-8 -*-
# ---------------------------------------------------------
# Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
# This file may not be copied, modified and/or distributed
# without the express permission of SYDRO Consult GmbH
# ---------------------------------------------------------
from __future__ import annotations
import bisect
import datetime
from enum import IntEnum
import calendar
import logging
import math
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class Timeseries():
    """
    Class for storing and manipulating time series

    Attributes:
        title (str): time series title
        station_id (str): station ID
        station_name (str): station name
        param (str): parameter which the time series represents (e.g. "P", "Q", etc.)
        unit (str): unit of the time series values
        location (str): location name
        lat (float): latitude coordinate
        lon (float): longitude coordinate
        z (float): altitude
        interpretation (int): interpretation code as defined in sydrodomain.ini
        nodes (dict): dictionary of timestamps and corresponding values (is not automatically sorted by date!)
    """

    class Interpretation(IntEnum):
        """
        Enum of interpretations as defined in sydrodomain.ini
        """
        Instantaneous = 1
        BlockRight = 2
        BlockLeft = 3
        Cumulative = 4
        CumulativePerTimestep = 5
        Undefined = 99


    def __init__(self, title: str = ""):
        """
        Instantiates a new Timeseries object

        :param title: Optional title
        """
        self.title = title
        self.station_id = "0"
        self.station_name = ""
        self.param = ""
        self.unit = ""
        self.location = ""
        self.lat = 0.0
        self.lon = 0.0
        self.z = 0.0
        self.interpretation = Timeseries.Interpretation.Undefined
        self.nodes = {} # {datum1: wert1, datum2: wert2,...} # are not automatically sorted by date!
        
    def add_node(self, timestamp: datetime.datetime, value: float) -> None:
        """
        Adds a new node consisting of timestamp, value to the timeseries

        If a timestamp already exists, it is overwritten and a corresponding warning log message is emitted

        :param timestamp: the timestamp of the node
        :param value: the value of the node (can be np.nan for Nan-values)
        :raises ValueError: if timestamp is not a valid datetime object
        """
        # check timestamp type
        if not isinstance(timestamp, datetime.datetime):
            if isinstance(timestamp, datetime.date):
                # convert from date to datetime
                timestamp = datetime.datetime(timestamp.year, timestamp.month, timestamp.day)
            else:
                raise ValueError("Timestamp %s of type %s is not a valid datetime!" % (timestamp, type(timestamp)))
                
        # remove any timezone information
        timestamp = timestamp.replace(tzinfo=None)
        
        if timestamp in self.nodes.keys():
            if not math.isclose(value, self[timestamp]):
                logger.warning(f"Replacing existing value for timestamp {timestamp:%Y-%m-%d %H:%M:%S} of {self[timestamp]} with new value of {value}!")
            
        self.nodes[timestamp] = value
        return
        
    def __getitem__(self, key):
        """
        allows for evaluation of self[key]
        allows ts.nodes[date] to be abbreviated to ts[date]
        """
        return self.nodes[key]
        
    def __setitem__(self, key, value):
        """
        allows assignment to self[key]
        allows ts.add_node(date, value) to be abbreviated to ts[date] = value
        NOTE: does not allow for reassignment of values of existing timestamps!
        """
        return self.add_node(key, value)
        
    def __iter__(self):
        """
        allows for iteration over the time series nodes
        yields a tuple of (date, value)
        """
        for date in self.dates:
            yield date, self.nodes[date]

    def __len__(self):
        """
        returns the length of the time series (number of nodes)
        """
        return len(self.nodes)
    
    def __repr__(self):
        """
        returns a string representation of the time series
        """
        if len(self) == 0: 
            return f"Timeseries {self.title} [{self.unit}], (length: {len(self)})"
        else:
            return f"Timeseries {self.title} [{self.unit}], {self.start:%d.%m.%Y %H:%M} - {self.end:%d.%m.%Y %H:%M} (length: {len(self)})"
    
    def plot(self, ax=None, **kwargs):
        """
        Creates a simple line plot of the time series

        :param ax: an optional matplotlib.axes.Axes object to use
        :param kwargs: keyword arguments passed to matplotlib.plot()
        :returns: list of `Line2D` objects
        """
        from matplotlib import pyplot as plt

        # create a new axes object if none is passed
        if not ax:
            _, ax = plt.subplots()

        # set default title
        if "label" not in kwargs:
            kwargs["label"] = f"{self.title} [{self.unit}]"

        # set drawstyle depending on interpretation
        if "drawstyle" not in kwargs:
            if self.interpretation == Timeseries.Interpretation.BlockRight:
                kwargs["drawstyle"] = "steps-post"
            elif self.interpretation == Timeseries.Interpretation.BlockLeft:
                kwargs["drawstyle"] = "steps-pre"
            elif self.interpretation == Timeseries.Interpretation.CumulativePerTimestep:
                kwargs["drawstyle"] = "steps-pre"
            else: 
                kwargs["drawstyle"] = "default"

        lines = ax.plot(self.dates, self.values, **kwargs)
        ax.legend()

        return lines
        
    def copy(self) -> Timeseries:
        """
        create a copy of the time series

        :returns: a copy of the Timeseries instance
        """
        copy = Timeseries(self.title)
        copy.station_id = self.station_id
        copy.station_name = self.station_name
        copy.param = self.param
        copy.unit = self.unit
        copy.location = self.location
        copy.lat = self.lat
        copy.lon = self.lon
        copy.z = self.z
        copy.nodes = self.nodes.copy() # shallow copy is sufficient as it only contains primitive types
        return copy
        
    def copy_metadata(self, ts: Timeseries) -> None:
        """
        copies metadata from a second time series to this timeseries

        :param ts: the time series from which to copy metadata
        """
        self.title = ts.title
        self.station_id = ts.station_id
        self.station_name = ts.station_name
        self.param = ts.param
        self.unit = ts.unit
        self.location = ts.location
        self.lat = ts.lat
        self.lon = ts.lon
        self.z = ts.z
        
        return
    
    @property
    def start(self) -> datetime.datetime:
        """
        :returns: the time series start date or None if the time series is empty
        """
        if len(self) == 0: 
            return None
        else:
            return sorted(self.nodes.keys())[0]

    @property
    def end(self) -> datetime.datetime:
        """
        :returns: the time series end date or None if the time series is empty
        """
        if len(self) == 0: 
            return None
        else:
            return sorted(self.nodes.keys())[-1]

    def cut(self, start: datetime.datetime, end: datetime.datetime) -> None:
        """
        cuts the time series to the period defined by start and end (inclusively)

        :param start: start date (inclusive)
        :param end: end date (inclusive)
        """
        dates = self.dates
        
        # find start index
        i_start = bisect.bisect_left(dates, start)
        
        # find end index
        i_end = bisect.bisect_left(dates, end, lo=i_start)
        
        # copy nodes between start and end
        new_nodes = {}
        for date in dates[i_start:i_end + 1]:
            new_nodes[date] = self.nodes[date]
            
        # replace nodes
        self.nodes = new_nodes

        return
        
    def write_to_file(self, filename: Path|str, options: dict = {}) -> None:
        """
        Writes the timeseries to a file

        Supported formats:
        * txt (with dateformat YYYYMMddHHmmss)
        * csv (with dateformat YYYY-MM-dd HH:mm:ss and comma as separator)
        * uvf
        * zrx
        * bin

        :param filename: path to file to write to. The file extension determines the format.
        :param options: optional dictionary with options, which can be format-specific

            Supported options:

            * ZRX format:
              * "REXCHANGE": a string that is used for setting the REXCHANGE header value
            * UVF format:
              * any key-value pair can be passed and will be written as an additional header entry in the format "key: value"
        """
        filename = Path(filename)

        # create directories if necessary
        if not filename.parent.exists():
            filename.parent.mkdir(parents=True, exist_ok=True)

        if filename.suffix.lower() == ".txt":
            # file format txt
            with open(filename, "w") as f:
                f.write("#" + self.title + "\n")
                for date, value in self:
                    f.write(date.strftime("%Y%m%d%H%M%S") + " " + str(value) + "\n")
            
        elif filename.suffix.lower() == ".csv":
            # file format csv
            with open(filename, "w") as f:
                f.write("#" + self.title + "\n")
                f.write("date,value\n")
                for date, value in self:
                    f.write(date.strftime("%Y-%m-%d %H:%M:%S") + "," + str(value) + "\n")
            
        elif filename.suffix.lower() == ".uvf":
            # file format uvf
            with open(filename, "w") as f:
                # optional header entries
                if self.interpretation != Timeseries.Interpretation.Undefined:
                    if self.interpretation == Timeseries.Interpretation.Instantaneous:
                        interpretation_str = "Linie"
                    elif self.interpretation == Timeseries.Interpretation.BlockRight:
                        interpretation_str = "Blockanfang"
                    elif self.interpretation == Timeseries.Interpretation.BlockLeft:
                        interpretation_str = "Blockende"
                    elif self.interpretation == Timeseries.Interpretation.Cumulative:
                        interpretation_str = "Summenlinie"
                    elif self.interpretation == Timeseries.Interpretation.CumulativePerTimestep:
                        interpretation_str = "Blockende"
                    f.write(f"$ib Funktion-Interpretation: {interpretation_str}\n")
                f.write(f"$sb Einheit: {self.unit}\n")
                #f.write("$sb Zeitschritt: m\n") TODO: timestep is unknown / may be variable
                f.write(f"$sb Beschreibung: {self.title}\n")
                if len(options) > 0:
                    for key, value in options.items():
                        f.write(f"{key}: {value}\n")
                
                # actual header
                f.write("*Z\n")
                # line with title, unit and start and end centuries
                century_start = str(self.start.year)[:2] + "00"
                century_end = str(self.end.year)[:2] + "00"
                f.write(self.title[:15].ljust(15) + self.unit.ljust(15) + century_start + " " + century_end + "\n")
                # line with location and coordinates
                f.write(self.location[:15].ljust(15) + ("%.9g" % self.lat).ljust(10) + ("%.9g" % self.lon).ljust(10) + ("%.9g" % self.z).ljust(10) + "\n")
                # line with start and end date
                date_begin = self.start
                date_end = self.end
                f.write(date_begin.strftime("%Y%m%d%H%M")[2:] + date_end.strftime("%Y%m%d%H%M")[2:] + "\n")
                
                # data
                for date, value in self:
                    if isinstance(value, float):
                        f.write(date.strftime("%Y%m%d%H%M")[2:] + (" %9.6g" % value) + "\n")
                    else:
                        f.write(date.strftime("%Y%m%d%H%M")[2:] + value.rjust(10) + "\n")
        
        elif filename.suffix.lower() == ".zrx":
            # file format ZRXP
            with open(filename, "w") as f:
                f.write(f"##{self.title}\n")
                f.write(f"#ZRXPVERSION3014.03|*|ZRXPCREATORSYDRO pyTimeseries|*|\n")
                f.write(f"#SANR{self.station_id}|*|SNAME{self.station_name}|*|\n")
                if "REXCHANGE" in options:
                    f.write(f"#REXCHANGE{options['REXCHANGE']}|*|\n")
                f.write(f"#CNAME{self.param}|*|CUNIT{self.unit}|*|RINVAL-777.0|*|\n")
                f.write(f"#LAYOUT(timestamp,value,remark)|*|\n")
                for date, value in self:
                    if isinstance(value, str) or np.isnan(value):
                        f.write(f"{date.strftime('%Y%m%d%H%M%S')} -777.0 \"{value}\"\n")
                    else:
                        f.write(f"{date.strftime('%Y%m%d%H%M%S')} {value}\n")
                        
        elif filename.suffix.lower() == ".bin":
            # SYDRO binary format
            # each record consists of a date as double (8 bytes) and the value as a single (4 bytes)
            with open(filename, "wb") as f:
                # write a header
                header = struct.pack("iii", *[3319, 0, 0])
                f.write(header)
                # write nodes
                for date, value in self:
                    # convert date to double
                    rdate = Timeseries._date_to_double(date)
                    # convert error values
                    if np.isnan(value):
                        value = -9999.999
                    # write record
                    record = struct.pack("df", *[rdate, value])
                    f.write(record)
                
        else:
            raise Exception("Unable to write timeseries to file with unknown extension: %s" % filename)
        return
        
    @property
    def dates(self) -> list[datetime.datetime]:
        """
        returns a sorted list of the dates contained in the timeseries

        :returns: list of datetime objects
        """
        return sorted(self.nodes.keys())

    @property
    def values(self) -> list[float]:
        """
        returns a list of the timeseries' values sorted by date

        :returns: list of values
        """
        values = [self.nodes[date] for date in sorted(self.nodes.keys())]
        return values
        
    def fill_gaps(self, dt: str = "M") -> None:
        """
        Fills date gaps with NaN values
        
        :param dt: timestep, either "d" for day or "M" for month (default)
        """
        if dt not in ["d", "M"]:
            raise ValueError("Invalid value for parameter dt!")
        
        # construct a list of equidistant dates from start to end
        date_list = [self.start]
        while True:
            if dt == "M":
                date = Timeseries._add_months(date_list[-1], 1)
            elif dt == "d":
                date = date_list[-1] + datetime.timedelta(1)
                
            if date <= self.end:
                date_list.append(date)
            else:
                break
                
        # get missing dates using set comparison
        dates_all = frozenset(date_list)
        dates_existing = frozenset(self.dates)
        dates_missing = dates_all - dates_existing
        
        # fill missing dates with NaN
        for date in dates_missing:
            self[date] = np.nan
        return
        
    def count_value_nodes(self) -> int:
        """
        Returns the number of nodes with non-NaN values in the time series

        :returns: number of non-NaN values (int)
        """
        return len([v for v in self.values if not np.isnan(v)])
        
    def delete_nan_nodes(self) -> None:
        """
        Deletes nodes with NaN values from the time series
        """
        # find dates with NaN values
        dates_nan = []
        for date, value in self:
            if np.isnan(value):
                dates_nan.append(date)
                
        # delete nodes
        for date in dates_nan:
            del self.nodes[date]
            
        return

    def delete_negative_nodes(self) -> None:
        """
        Deletes nodes with negative values from the time series
        """
        # find dates with negative values
        dates_negative = []
        for date, value in self:
            if value < 0:
                dates_negative.append(date)
                
        # delete nodes
        for date in dates_negative:
            del self.nodes[date]
            
        return
        

    @staticmethod
    def read_file(filename: Path|str, format: str = None) -> Timeseries:
        """
        Reads a timeseries from a file

        supported formats:
        * uvf
        * zrx
        * bin
        
        :param filename: path to file to read
        :param format: optional format such as "uvf", "zrx", etc. If not provided, the file extension is used instead
        
        NOTE: title is *not* read from the file
        """
        filename = Path(filename)
        
        if format == None:
            # use file extension
            format = filename.suffix.lstrip(".")

        format = format.lower()
        
        if format == "uvf":
            # file format uvf
            ts = Timeseries._read_uvf(filename)
        
        elif format == "zrx":
            # file format zrxp
            ts = Timeseries._read_zrx(filename)

        elif format == "bin":
            # SYDRO binary format
            ts = Timeseries._read_bin(filename)
                
        else:
            raise Exception("Unable to read timeseries file with unknown extension: %s" % filename)
        
        return ts
            

    @staticmethod
    def _read_uvf(filename: Path|str) -> Timeseries:
        """
        Reads a timeseries from a UVF file
        """
        filename = Path(filename)

        i_line = 0
        i_header = 0
        is_attributes = True
        is_header = False
        is_data = False
        century = 1900
        year = 0 # two-digit year
        
        ts = Timeseries()
        
        f = open(filename, "r")
        for line in f:

            i_line += 1

            if line.startswith("*Z"):
                # header starts here
                is_attributes = False
                is_header = True

            if is_attributes:
                # skip attributes
                pass

            if is_header:
                i_header += 1
                if i_header == 1:
                    pass
                elif i_header == 2:
                    # read the title, unit and the century
                    ts.title = line[:15]
                    ts.unit = line[15:30]
                    century = int(line[30:34])
                elif i_header == 3:
                    # read the location
                    try:
                        ts.location = line[:15]
                        ts.lat = float(line[15:25])
                        ts.lon = float(line[25:35])
                        ts.z = float(line[35:45])
                    except:
                        print("Unable to read location parameters")

                elif i_header == 4:
                    pass
                else:
                    # section with data begins here
                    is_header = False
                    is_data = True
            
            if is_data:
                if len(line.strip()) > 0:
                    date_str = line[:10]
                    value_str = line[10:].strip()
                    if value_str.startswith("-777"):
                        # convert error values to nan
                        value = np.nan
                    else:
                        value = float(value_str)
                    # determine century by comparing with last two-digit year
                    if int(date_str[:2]) < year:
                        century += 100
                    # store the new two-digit year
                    year = int(date_str[:2])
                    # complete the date string by prepending the century
                    date_str = str(century)[:2] + date_str
                    # parse date
                    date = datetime.datetime.strptime(date_str, "%Y%m%d%H%M")
                    
                    # store data
                    ts.add_node(date, value)
        f.close()
        
        return ts
        
    @staticmethod
    def _read_zrx(filename: Path|str) -> Timeseries:
        """
        Reads a timeseries from a ZRX file
        """
        filename = Path(filename)

        metadata = {"SANR": 0, "SNAME": "", "CNAME": "", "CUNIT": "", "RINVAL": "-777.0"} # only the ones relevant to us
        
        ts = Timeseries()
        
        with open(filename, "r") as f:
            for line in f:
                if line.startswith("##"):
                    # skip comments
                    continue
                elif line.startswith("#"):
                    # read metadata
                    line = line[1:] # remove "#" from the bgeinning
                    if "|*|" in line:
                        data = line.split("|*|")
                    elif ";*;" in line:
                        data = line.split(";*;")
                    else:
                        data = []
                    # parse metadata
                    for block in data:
                        for key in metadata.keys():
                            if block.startswith(key):
                                value = block[len(key):]
                                metadata[key] = value
                else:
                    date_str, value_str = line.split()[:2]
                    # parse date
                    if len(date_str) < 14:
                        # fill missing parts with 0
                        date_str = date_str.ljust(14, "0")
                    date = datetime.datetime.strptime(date_str, "%Y%m%d%H%M%S")
                    # parse value
                    if value_str.startswith(metadata["RINVAL"]):
                        # convert error values to nan
                        value = np.nan
                    else:
                        value = float(value_str)
                    
                    # store value as node
                    ts.add_node(date, value)
                    
            # store metadata
            ts.title = metadata["SNAME"]
            ts.station_id = metadata["SANR"]
            ts.station_name = metadata["SNAME"]
            ts.param = metadata["CNAME"]
            ts.unit = metadata["CUNIT"]

        return ts
        
    @staticmethod
    def _read_bin(filename: Path|str) -> Timeseries:
        """
        Reads a timeseries from a BIN file
        """
        filename = Path(filename)

        # each record consists of a date as double (8 bytes) and the value as a single (4 bytes)
       
        ts = Timeseries()
        
        with open(filename, "rb") as f:
            # skip the header
            f.read(12)
            # read records
            while True:
                chunk = f.read(12)
                if chunk:
                    rDate, value = struct.unpack("df", chunk)
                    # convert double date to datetime
                    timestamp = Timeseries._double_to_date(rDate)
                    # convert error values
                    if abs(value - -9999.999) < 0.0001:
                        value = np.nan
                    # store as node
                    ts.add_node(timestamp, value)
                else:
                    break
                    
        return ts

    @staticmethod
    def read_wbl(filename: Path|str, series: str|list[str] = []) -> list[Timeseries]:
        """
        Class method for reading one or more series from a WBL file
        
        :param filename: path to WBL wile
        :param series: series name or list of series names to read, if no series names are passed, all series will be read
        :returns: list of Timeseries instances in the same order as the series names
        """
        if not isinstance(series, list):
            series = [series]

        filename = Path(filename)

        names, columns, datatype = Timeseries._read_welinfo(filename)
        if len(columns) == 0:
            raise Exception("Unable to read series information from WELINFO file!")

        if datatype == 1:
            datalength = 4 # integer
        elif datatype == 2:
            datalength = 4 # single
        elif datatype == 3:
            datalength = 8 # double
        elif datatype == 4:
            datalength = 1 # boolean
        else:
            raise Exception(f"Unknown datatype {datatype} encountered!")
            
        units = [col[3] for col in columns]

        if len(series) == 0:
            # if no series names were passed, import all available series
            series = names

        # get selected indices
        indices = []
        for seriesname in series:
            if seriesname not in names:
                raise Exception(f"Series '{seriesname}' not found in file!")
            indices.append(names.index(seriesname))

        # instantiate time series
        ts_dict = {} # {name: ts, ...}
        for name, unit in zip(names, units):
            ts_dict[name] = Timeseries(name)
            ts_dict[name].station_name = name
            ts_dict[name].unit = unit
            ts_dict[name].interpretation = Timeseries.Interpretation.BlockRight

        with open(filename, "rb") as f:
            # skip header (same length as a single record consisting of 8 bytes date and x bytes for each value depending on the data type
            f.read(8 + datalength * len(columns))
            # read records
            while True:
                # read date as double
                chunk = f.read(8)
                if chunk:
                    rDate, = struct.unpack("d", chunk)
                    # convert double date to datetime
                    timestamp = Timeseries._double_to_date(rDate)
                else:
                    # end of file
                    break

                # read values
                position = 0
                for index in sorted(indices):

                    # skip to index location
                    f.read(datalength * (index - position))

                    # read data
                    chunk = f.read(datalength)

                    # convert bytes to proper data type
                    if datatype == 1:
                        value, = struct.unpack("i", chunk) # integer
                    elif datatype == 2:
                        value, = struct.unpack("f", chunk) # single
                    elif datatype == 3:
                        value, = struct.unpack("d", chunk) # double
                    elif datatype == 4:
                        value, = struct.unpack("?", chunk) # boolean

                    # convert value to float
                    value = float(value)

                    # convert error values
                    if abs(value - -9999.999) < 0.0001:
                        value = np.nan

                    # add node
                    ts_dict[names[index]].add_node(timestamp, value)

                    # update position
                    position = index + 1

                # skip ahead to next timestamp
                f.read(datalength * (len(columns) - position))

        return [ts_dict[seriesname] for seriesname in series]

    @staticmethod
    def read_wel(filename: Path|str, series: str|list[str] = []) -> list[Timeseries]:
        """
        Class method for reading one or more series from a WEL file
        Also supports WBL files
        
        :param filename: path to WEL/WBL file
        :param series: series name or list of series names to read, if no series names are passed, all series will be read
        :returns: list of Timeseries instances in the same order as the series names
        """
        filename = Path(filename)

        if not isinstance(series, list):
            series = [series]

        if filename.suffix.lower() == ".wbl":
            return Timeseries.read_wbl(filename, series)

        series_available = {} # dictionary of series available in file: {index: name, ...} (index starts at 1!)
        indices_to_import = [] # list of series indices to import
        ts_dict = {} # dictionary for storing Timeseries instances: {index: ts, ...}

        with open(filename, "r") as f:
            for i, line in enumerate(f, start=1):
                line = line[1:].rstrip() # remove leading space and trailing line-break
                if i == 1:
                    # skip first line
                    continue
                elif i == 2:
                    # second line contains series names
                    n = len(line) // 16

                    # read all available series names and store in dict with index
                    for idx in range(1, n):
                        name = line[idx*16:(idx*16)+16].strip()
                        series_available[idx] = name

                    # determine series indices to import
                    if len(series) == 0:
                        # if no series names were passed, import all available series
                        indices_to_import = list(series_available.keys())
                    else:
                        # collect indices of passed series names 
                        for name_to_import in series:
                            for idx, name in series_available.items():
                                if name == name_to_import:
                                    indices_to_import.append(idx)
                                    break
                            else:
                                raise Exception(f"Series '{name_to_import}' not found in file!")

                elif i == 3:
                    # third line contains series units
                    # read units and instantiate time series
                    for idx in indices_to_import:
                        unit = line[idx*16:(idx*16)+16].strip()
                        name = series_available[idx]
                        ts_dict[idx] = Timeseries(name)
                        ts_dict[idx].station_name = name
                        ts_dict[idx].unit = unit
                        ts_dict[idx].interpretation = Timeseries.Interpretation.BlockRight
                else:
                    # read data
                    datestring = line[:16]
                    # HACK: workaround for bug #182 in Talsim where time is missing from timestamp
                    if datestring.endswith("  :  "):
                        datestring = datestring[:12] + "00:00"
                    date = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M")
                    for idx in indices_to_import:
                        string = line[idx*16:(idx*16)+16]
                        try:
                            value = float(string)
                        except ValueError:
                            value = np.nan
                            logger.warning(f"Timestamp {datestring}: interpreting value of {string} for {series_available[idx]} as NaN!")
                        ts_dict[idx].add_node(date, value)
        
        # return list of timeseries in order of passed series names
        return [ts_dict[idx] for idx in indices_to_import]

    @staticmethod
    def _read_welinfo(filename: Path|str) -> tuple[list, list, int]:
        """
            Class method for reading the WELINFO file that accompanies a WEL file.
            Returns a list with the series names in the WEL file.
            :param filename: path to WELINFO file
            :returns: list of series names, list of columns and the datatype of the values in the WEL file
        """
        filename = Path(filename)
        file_welinfo = filename.with_suffix(".WELINFO")
        if not file_welinfo.exists():
            raise Exception(f"Required WELINFO file not found: {file_welinfo}")

        # read WELINFO
        columns = [] 
        with open(file_welinfo, "r") as f:

            isdata = False
            for line in f:

                if not isdata and line.startswith("Datentyp="):
                    datatype = int(line.split("=")[1])
                    continue

                if not isdata and line.startswith("[Elemente]"):
                    isdata = True
                    continue

                if isdata:
                    # example
                    """
                    A000_1ZU;Inflow;R127C66;m3/s;     0
                    A000_NIE;Rainfall;R127C66;mm;     1
                    A000_NEF;Eff_Rainfall;R127C66;mm;     2
                    A000_TEM;Airtemperature;R127C66;oC;     3
                    """
                    columns.append(line.strip().split(";"))

        names = [col[0] for col in columns]

        return names, columns, datatype

    @staticmethod
    def read_wel_to_dataframe(filename: Path|str, series: str|list[str] = []) -> pd.DataFrame:
        """
        Class method for reading one or more series from a WEL file as a pandas Dataframe
        
        :param filename: path to WEL file
        :param series: series name or list of series names to read, if no series names are passed, all series will be read
        :returns: pandas DataFrame
        """
        filename = Path(filename)

        if not isinstance(series, list):
            series = [series]

        kwargs = {}
        if len(series) > 0:
            # read only selected series
            kwargs["usecols"] = ["Datum_Zeit"] + series
        else:
            # read all series
            pass

        # do not use panda's "infer" method for the colspecs because that is based only on the first 100 lines of the file
        # and if numbers get larger later on, they may be cut off!
        # therefore we need to determine the number of columns in the file first, and then explicitly set the colspecs
        colwidth = 16
        with open(filename, "r") as f:
            for i, line in enumerate(f, start=1):
                if i == 2:
                    # use the second line with column titles to determine the number of columns
                    line = line[1:].rstrip() # remove leading space and trailing line-break
                    assert len(line) % colwidth == 0, "Unable to determine number of columns in WEL file!"
                    n_cols = len(line) // colwidth
                elif i > 2:
                    break
        
        colspecs = []
        start = 1
        for i in range(0, n_cols):
            end = start + colwidth
            colspecs.append((start, end))
            start = end

        # read the file in chunks
        reader = pd.read_fwf(filename, colspecs=colspecs, skiprows=[0, 2], index_col=0, parse_dates=True, dayfirst=True, chunksize=1000, **kwargs)
        df = pd.concat([chunk for chunk in reader])

        return df        


    @staticmethod  
    def read_fews(filename: Path|str) -> dict:
        """
        Reads timeseries from a FEWS PI Timeseries XML file

        Schema: http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd
        
        :param filename: path to xml input file
        :return: dict of nested timeseries {location_id: {parameter_id: Timeseries, ...}, ...}
        """
        filename = Path(filename)

        logger.info(f"Reading FEWS PI Timeseries XML file {filename.name}...")
        
        result = {} # {location_id: {parameter_id: ts, ...}, ...}
        
        ns = {"PI": "http://www.wldelft.nl/fews/PI"}
        tree = ET.parse(filename)
        root = tree.getroot()
        for series in root.findall("PI:series", ns):
            try:
                # read header
                header = series.find("PI:header", ns)
                type_ = header.find("PI:type", ns).text
                location_id = header.find("PI:locationId", ns).text
                parameter_id = header.find("PI:parameterId", ns).text
                station_name = header.find("PI:stationName", ns).text
                unit = header.find("PI:units", ns).text
                error_value = header.find("PI:missVal", ns).text
                
                if not location_id in result:
                    result[location_id] = {}
                if parameter_id in result[location_id]:
                    logger.warning(f"Duplicate parameterID {parameter_id} for locationId {location_id} found! Overwriting existing data!")

                result[location_id][parameter_id] = None
                
                # create a new timeseries
                ts = Timeseries()
                ts.title = location_id + "." + parameter_id
                ts.param = parameter_id
                ts.station_name = location_id + "." + station_name
                ts.unit = unit
                ts.station_id = location_id

                # map type to interpretation
                if type_ == "instantaneous":
                    ts.interpretation = Timeseries.Interpretation.Instantaneous
                elif type_ == "mean":
                    ts.interpretation = Timeseries.Interpretation.BlockRight
                elif type_ == "accumulative":
                    ts.interpretation = Timeseries.Interpretation.CumulativePerTimestep
                else:
                    raise Exception(f"Unexpected type '{type_}' for locationId {location_id}, parameterId {parameter_id}!")

                # read events and add nodes
                for event in series.findall("PI:event", ns):
                    #<event date="2021-07-05" time="16:30:00" value="177" flag="2" />
                    #print(event.attrib)
                    date = event.attrib["date"]
                    time = event.attrib["time"]
                    flag = int(event.attrib["flag"])
                    value_str = event.attrib["value"]
                    # value error checking
                    if value_str.strip() == "" or value_str == error_value:
                        value = np.nan
                    else:
                        value = float(value_str)
                    # parse date
                    t = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
                    # add node
                    ts.add_node(t, value)
                
                logger.info(f"Read {len(ts.nodes)} values for {ts.title}...")

                result[location_id][parameter_id] = ts
            
            except Exception as e:
                logger.error(f"Error while reading series {series}!")
                logger.error(e)
                
        return result


    @staticmethod
    def write_fews(filename: Path|str, ts_dict: dict) -> None:
        """
        Writes timeseries to a FEWS PI Timeseries XML file

        Schema: http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd

        :param filename: path to XML file to write
        :param ts_dict: nested dictionary of timeseries to write {location_id: {parameter_id: Timeseries, ...}, ...}
        """

        logger.info(f"Writing FEWS PI Timeseries XML file...")
        
        # build an xml tree structure
        xmlroot = ET.Element("TimeSeries")
        xmlroot.set("xmlns", "http://www.wldelft.nl/fews/PI")
        xmlroot.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        xmlroot.set("xsi:schemaLocation", "http://www.wldelft.nl/fews/PI http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd")
        xmlroot.set("version", "1.2")
        xmltimeZone = ET.SubElement(xmlroot, "timeZone")
        xmltimeZone.text = "0.0"
        # loop over dictionary items and add a <series> tag for each timeseries
        for location_id, param_dict in ts_dict.items():
            for parameter_id, ts in param_dict.items():
                """
                <series>
                    <header>
                        <type>instantaneous</type>
                        <locationId>ZI-A13140</locationId>
                        <parameterID>BOF</parameterID>
                        <timeStep unit="nonequidistant" />
                        <startDate date="2020-06-16" time="15:30:00" />
                        <endDate date="2020-06-17" time="15:29:00" />
                        <missVal>-999.0</missVal>
                        <stationName>Halde PH4</stationName>
                        <units>M3D</units>
                    </header>
                    <event date="2021-01-12" time="11:01:02" value="11" flag="2" />
                </series>
                """
                xmlseries = ET.SubElement(xmlroot, "series")
                # header
                xmlheader = ET.SubElement(xmlseries, "header")

                # type (interpretation)
                xmltype = ET.SubElement(xmlheader, "type")
                if ts.interpretation == Timeseries.Interpretation.Instantaneous:
                    xmltype.text = "instantaneous"
                elif ts.interpretation == Timeseries.Interpretation.BlockRight:
                    #TODO: not sure whether "mean" corresponds to BlockRight or BlockLeft?
                    xmltype.text = "mean"
                elif ts.interpretation == Timeseries.Interpretation.CumulativePerTimestep:
                    xmltype.text = "accumulative"
                else:
                    raise Exception(f"Interpretation {ts.interpretation} is not supported in FEWS PI Timeseries XML files!")
                
                xmllocationId = ET.SubElement(xmlheader, "locationId")
                xmllocationId.text = location_id
                xmlparameterId = ET.SubElement(xmlheader, "parameterId")
                xmlparameterId.text = parameter_id
                xmltimeStep = ET.SubElement(xmlheader, "timeStep")
                xmltimeStep.set("unit", "nonequidistant")
                xmlstartdate = ET.SubElement(xmlheader, "startDate")
                startdate = ts.start
                xmlstartdate.set("date", startdate.strftime("%Y-%m-%d"))
                xmlstartdate.set("time", startdate.strftime("%H:%M:%S"))
                xmlenddate = ET.SubElement(xmlheader, "endDate")
                enddate = ts.end
                xmlenddate.set("date", enddate.strftime("%Y-%m-%d"))
                xmlenddate.set("time", enddate.strftime("%H:%M:%S"))
                xmlmissVal = ET.SubElement(xmlheader, "missVal")
                xmlmissVal.text = "-999.0"
                xmlstationName = ET.SubElement(xmlheader, "stationName")
                xmlstationName.text = ts.station_name
                xmlunits = ET.SubElement(xmlheader, "units")
                xmlunits.text = ts.unit
                # events
                for timestamp, value in ts:
                    xmlevent = ET.SubElement(xmlseries, "event")
                    if np.isnan(value):
                        value = "-999.0"
                    else:
                        value = f"{value}"
                    xmlevent.set("date", timestamp.strftime("%Y-%m-%d"))
                    xmlevent.set("time", timestamp.strftime("%H:%M:%S"))
                    xmlevent.set("value", value)
                    xmlevent.set("flag", "2") #TODO: meaningful flag value?
            
        ET.indent(xmlroot, "    ")
        xmlstring = ET.tostring(xmlroot, encoding="unicode", xml_declaration=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(xmlstring)
            
        return


    @staticmethod
    def _add_months(sourcedate: datetime.datetime, months: int) -> datetime.datetime:
        """
        Funktion zum addieren von Monaten zu einem Datum
        
        :param sourcedate: Ausgangsdatum als datetime.datetime
        :param months: Anzahl Monate
        :returns: Das neue Datum als datetime.datetime
        """
        month = sourcedate.month - 1 + months
        year = int(sourcedate.year + month / 12)
        month = month % 12 + 1
        day = min(sourcedate.day, calendar.monthrange(year, month)[1])
        return datetime.datetime.combine(datetime.date(year, month, day), sourcedate.time())
    
    @staticmethod
    def synchronize(ts1: Timeseries, ts2: Timeseries) -> tuple[Timeseries, Timeseries]:
        """
        Synchronizes two time series by only keeping the nodes with identical dates/times.
        
        :param ts1: 1st Timeseries
        :param ts2: 2nd Timeseries
        :returns: tuple of two new synchronized Timeseries
        """
        ts1_dates = frozenset(ts1.dates)
        ts2_dates = frozenset(ts2.dates)
        
        ts1_sync = ts1.copy()
        ts2_sync = ts2.copy()
        
        # remove unwanted nodes from ts1
        diff = ts1_dates - ts2_dates
        for date in diff:
            del ts1_sync.nodes[date]
        
        # remove unwanted nodes from ts2
        diff = ts2_dates - ts1_dates
        for date in diff:
            del ts2_sync.nodes[date]
        
        return (ts1_sync, ts2_sync)

           
    @staticmethod
    def _date_to_double(timestamp: datetime.datetime) -> float:
        """
        converts a datetime to a double date defined as hours since 01.01.1601

        :param timestamp: the timestamp to convert
        :returns: a float value of the number of hours since 01.01.1601
        """
        td = timestamp - datetime.datetime(1601, 1, 1)
        return td.total_seconds() / 3600.0
    
    @staticmethod
    def _double_to_date(rDate: float) -> datetime.datetime:
        """
        converts a double date to a datetime object. Assumes the double date is defined as hours since 01.01.1601

        :param rDate: value to convert
        :returns: datetime object
        """
        refdate = datetime.datetime(1601, 1, 1)
        timestamp = refdate + datetime.timedelta(hours=rDate)
        return timestamp

    @staticmethod
    def to_dataframe(timeseries: Timeseries|list[Timeseries]) -> pd.DataFrame:
        """
        Converts a list of Timeseries to a pandas.DataFrame

        :param timeseries: a Timeseries object (or list of Timeseries objects) to convert
        :returns: the DataFrame
        """
        if not isinstance(timeseries, list):
            timeseries = [timeseries]

        df_list = []
        for ts in timeseries:
            if not isinstance(ts, Timeseries):
                raise ValueError(f"Parameter {type(ts)} is not a Timeseries object!")
            df_list.append(pd.DataFrame.from_dict(ts.nodes, orient="index", columns=[ts.title]))
        df = pd.concat(df_list, axis=1)
        return df

    @staticmethod
    def from_series(series: pd.Series) -> Timeseries:
        """
        Converts a pandas Series to a Timeseries

        :param series: the Series to convert
        :return: the Timeseries
        """
        ts = Timeseries(series.name)
        dates = [pd.Timestamp(t64).to_pydatetime() for t64 in series.index]
        values = series.values
        nodes = {t: v for t, v in zip(dates, values)}
        ts.nodes = nodes
        return ts
