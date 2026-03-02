"""
Value object: ClientStatus enum.
"""

from enum import Enum


class ClientStatus(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    PROSPECTO = "prospecto"
