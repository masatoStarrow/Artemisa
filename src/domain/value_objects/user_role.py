"""
Value object: UserRole enum.
"""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    SOPORTE = "soporte"
    COMERCIAL = "comercial"
