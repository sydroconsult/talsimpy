# -*- coding: utf-8 -*-
# ---------------------------------------------------------
# Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
# This file may not be copied, modified and/or distributed
# without the express permission of SYDRO Consult GmbH
# ---------------------------------------------------------
from dataclasses import dataclass, field

@dataclass
class WelInfoEntry:
    """
    Information about a single series entry in a WELINFO file

    Attributes:
        series (str): series name
        state (str): state represented by the series (e.g. "Inflow", "Outflow", etc.)
        element (str): associated element/state name (e.g. "sub-basin X", "reservoir Y", etc.)
        unit (str): unit of the series (e.g. "m3/s")
        index (int): index of the series in the WEL/WBL file (starting at 0)
    """
    series: str
    state: str
    element: str
    unit: str
    index: int


@dataclass
class WelInfo:
    """
    Information read from a WELINFO file

    Attributes:
        datatype (int): datatype of the values in the WBL file (1: integer, 2: single, 3: double, 4: boolean)
        entries (list[WelInfoEntry]): list of WelInfoEntry objects representing the series in the WELINFO file
    """
    datatype: int
    entries: list[WelInfoEntry] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        """series names"""
        return [entry.series for entry in self.entries]

    @property
    def units(self) -> list[str]:
        """series units"""
        return [entry.unit for entry in self.entries]


