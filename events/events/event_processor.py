import logging
import json

from events import interview_complete, interview_approved
from shared.events import EventType
from shared.data.database import Database


def process_message(db: Database, message_body: str):
    """
    Process the message from SQS based on event type.

    Args:
        message_body: The parsed JSON message body
    """
    logging.info(f"Processing message body: {json.dumps(message_body)}")

    # Extract event type and interview ID
    event_type = message_body.get('event_type')
    interview_id = message_body.get('interview_id')

    if not event_type or not interview_id:
        raise ValueError("Message missing required fields: event_type and interview_id")

    logging.info(f"processing event_type: {event_type}, interview_id: {interview_id}")

    # Process based on event type
    if event_type == EventType.INTERVIEW_COMPLETE.value:
        interview_complete.process(db, interview_id)

    elif event_type == EventType.INTERVIEW_APPROVED.value:
        interview_approved.process(db, interview_id)

    else:
        logging.warning(f"Unknown event type: {event_type}")
