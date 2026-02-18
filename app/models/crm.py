"""Pydantic models for CRM / Customer data."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Customer(BaseModel):
    """Represents a single CRM customer record."""
    customer_id: int = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address")
    created_at: datetime = Field(..., description="Account creation timestamp")
    status: CustomerStatus = Field(..., description="Current account status")
