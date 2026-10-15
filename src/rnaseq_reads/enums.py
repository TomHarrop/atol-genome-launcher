#!/usr/bin/env python3

from enum import StrEnum


class ReadNumber(StrEnum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"


class Platform(StrEnum):
    ILLUMINA = "ILLUMINA"
    OXFORD_NANOPORE = "OXFORD_NANOPORE"
