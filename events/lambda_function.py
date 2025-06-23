import json
import logging

from shared.log import log
from events.event_processor import process_message
from shared.data.database import Database


# initialize database client
db = Database()


def lambda_handler(event, context):
    """
    Lambda function to process messages from SQS queue.
    Processes one message at a time.

    Args:
        event: The event dict from SQS
        context: The Lambda context object

    Returns:
        dict: Response with processing status
    """
    logging.info(f"Received event: {json.dumps(event)}")

    # Check if this is a direct invocation for testing
    if 'Records' not in event:
        logging.info("Direct invocation detected, returning event")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'event': event})
        }

    # Process each record (should only be one due to batch_size=1)
    for record in event['Records']:
        message_id = record['messageId']
        # receipt_handle = record['receiptHandle']
        body = record['body']

        logging.info(f"Processing message id {message_id}")

        try:
            # Parse the message body
            message_body = json.loads(body)

            # Process the message based on event type
            process_message(db, message_body)

            logging.info(f"Successfully processed message {message_id}")

        except Exception as e:
            logging.error(f"Error processing message {message_id}: {str(e)}")
            raise

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully processed {len(event["Records"])} messages'
        })
    }
