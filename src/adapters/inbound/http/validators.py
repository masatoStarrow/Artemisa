"""
Data validation functions using Pydantic v2 field validators.

This module provides comprehensive validation functions for user and client data,
ensuring data integrity and security across the application.
"""
import re
from typing import Any


def validate_non_empty_name(value: str) -> str:
    """
    Validate that name fields are non-empty and contain only valid characters.
    
    Args:
        value: The name string to validate
        
    Returns:
        str: The validated name value
        
    Raises:
        ValueError: If name is empty, too short, or contains invalid characters
    """
    if not value or not value.strip():
        raise ValueError("Name cannot be empty")
    
    # Remove extra whitespace
    clean_value = value.strip()
    
    # Check minimum length
    if len(clean_value) < 2:
        raise ValueError("Name must be at least 2 characters long")
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']+$", clean_value):
        raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")
    
    # Check for numbers
    if re.search(r'\d', clean_value):
        raise ValueError("Name cannot contain numbers")
    
    return clean_value


def validate_phone_format(value: str) -> str:
    """
    Validate phone number format for international compatibility.
    
    Args:
        value: The phone number string to validate
        
    Returns:
        str: The validated phone number
        
    Raises:
        ValueError: If phone format is invalid
    """
    if not value or not value.strip():
        raise ValueError("Phone number cannot be empty")
    
    # Remove all non-digit characters for validation
    digits_only = re.sub(r'[^\d]', '', value.strip())
    
    # Check length (8-15 digits for international compatibility) 
    if len(digits_only) < 8:
        raise ValueError("Phone number must have at least 8 digits")
    if len(digits_only) > 15:
        raise ValueError("Phone number cannot exceed 15 digits")
    
    # Return original formatted value
    return value.strip()


def validate_company_name(value: str) -> str:
    """
    Validate company name format and constraints.
    
    Args:
        value: The company name string to validate
        
    Returns:
        str: The validated company name
        
    Raises:
        ValueError: If company name format is invalid
    """
    if not value or not value.strip():
        raise ValueError("Company name cannot be empty")
    
    clean_value = value.strip()
    
    # Check length constraints
    if len(clean_value) < 2:
        raise ValueError("Company name must be at least 2 characters long")
    if len(clean_value) > 255:
        raise ValueError("Company name cannot exceed 255 characters")
    
    # Allow letters, numbers, spaces, and common business characters
    if not re.match(r"^[a-zA-ZÀ-ÿ0-9\s\-\&\.\,\(\)]+$", clean_value):
        raise ValueError("Company name contains invalid characters")
    
    return clean_value


def validate_notes_length(value: str) -> str:
    """
    Validate notes field length constraints.
    
    Args:
        value: The notes string to validate
        
    Returns:
        str: The validated notes value
        
    Raises:
        ValueError: If notes exceed length limits
    """
    if not value:
        return value  # Empty notes are allowed
    
    clean_value = value.strip()
    
    if len(clean_value) > 1000:
        raise ValueError("Notes cannot exceed 1000 characters")
    
    return clean_value