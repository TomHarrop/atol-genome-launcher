#!/usr/bin/env python3

from pydantic import BaseModel
from typing import Optional


class BpaFile(BaseModel):
    """
    A single remote file on BPA
    """

    url: str
    md5sum: str
    lane_number: Optional[str] = "single_lane"


class ReadFile(BaseModel):
    name: str
    data_type: str
    r1: Optional[list[BpaFile]] = None
    r2: Optional[list[BpaFile]] = None
    single_end: Optional[list[BpaFile]] = None


class Manifest(BaseModel):

    read_files: list[ReadFile]
