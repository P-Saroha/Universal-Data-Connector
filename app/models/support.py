"""Pydantic models for Support Ticket data."""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TicketPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class SupportTicket(BaseModel):
    """Represents a single support ticket."""
    ticket_id: int = Field(..., description="Unique ticket identifier")
    customer_id: int = Field(..., description="Associated customer ID")
    subject: str = Field(..., description="Ticket subject line")
    priority: TicketPriority = Field(..., description="Ticket priority level")
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    status: TicketStatus = Field(..., description="Current ticket status")
