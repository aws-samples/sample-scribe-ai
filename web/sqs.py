import json
import logging
import boto3
import os
from typing import Dict, Any, Optional

from shared.config import config

logger = logging.getLogger(__name__)

def post_message(event_type: str, interview_id: str, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Posts a message to an SQS queue with the specified event type and interview ID.

    Args:
        event_type: The type of event being recorded
        interview_id: The ID of the interview associated with this event
        additional_data: Optional dictionary of additional data to include in the message

    Returns:
        The response from SQS send_message call

    Raises:
        Exception: If there's an error posting the message to SQS
    """
    try:
        # Get the queue URL from environment variable
        if not config.sqs_queue_url:
            logger.error("SQS_QUEUE_URL environment variable not set")
            raise ValueError("SQS_QUEUE_URL environment variable not set")

        # Create SQS client
        sqs = boto3.client('sqs')

        # Prepare message body
        message_body = {
            'event_type': event_type,
            'interview_id': interview_id,
        }

        # Add additional data if provided
        if additional_data:
            message_body.update(additional_data)

        # Send message to SQS queue
        response = sqs.send_message(
            QueueUrl=config.sqs_queue_url,
            MessageBody=json.dumps(message_body)
        )

        logger.info(f"Message sent to SQS: {event_type} for interview {interview_id}")
        return response

    except Exception as e:
        logger.error(f"Error posting message to SQS: {str(e)}")
        raise
