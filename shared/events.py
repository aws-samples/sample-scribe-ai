from enum import Enum


class EventType(Enum):
    """Enum for event type values"""

    INTERVIEW_COMPLETE = "interview_complete"
    INTERVIEW_APPROVED = "interview_approved"
