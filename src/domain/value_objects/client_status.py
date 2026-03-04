"""
Value object: ClientStatus enum.
"""

from enum import Enum


class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
