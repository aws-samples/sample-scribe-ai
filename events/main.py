import json
import uuid
import logging
import sys

import requests
import lambda_function
from shared.events import EventType


def main():

    # get interview_id passed in from cli arg
    test_interview_id = sys.argv[1]

    # test_local(test_interview_id)
    test_local_container(test_interview_id)


def test_local_container(interview_id):
    """
    Test the Lambda function running in a local container by posting mock SQS events.
    """

    logging.info(f"Using test interview ID: {interview_id}")

    post_event_to_container(EventType.INTERVIEW_COMPLETE.value, interview_id)


def post_event_to_container(event_type, interview_id):
    """
    Create a mock SQS event and post it to the local Lambda container.

    Args:
        event_type: The type of event to create
        interview_id: The interview ID to use in the event
    """
    print(f"\n=== Testing {event_type} event in container ===")
    event = create_mock_sqs_event(event_type, interview_id)
    post_to_container(event)


def post_to_container(payload):
    """
    Post a payload to the local Lambda container and handle the response.

    Args:
        payload: The payload to send to the Lambda container
    """

    try:
        response = requests.post(
            "http://localhost:8090/2015-03-31/functions/function/invocations",
            data=json.dumps(payload)
        )

        # Check if the request was successful
        if response.status_code == 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error making request to container: {str(e)}")


def test_local():
    """
    Main function to test the Lambda handler with mock SQS events.
    """
    # Generate a test interview ID
    test_interview_id = "interview-" + str(uuid.uuid4())[:8]
    print(f"Using test interview ID: {test_interview_id}")

    # Test interview_complete event
    print("\n=== Testing interview_complete event ===")
    event_complete = create_mock_sqs_event(
        "interview_complete", test_interview_id)
    res_complete = lambda_function.lambda_handler(
        event_complete, {"context": True})
    print(f"Response: {json.dumps(res_complete, indent=2)}")

    # Test interview_approved event
    print("\n=== Testing interview_approved event ===")
    event_approved = create_mock_sqs_event(
        "interview_approved", test_interview_id)
    res_approved = lambda_function.lambda_handler(
        event_approved, {"context": True})
    print(f"Response: {json.dumps(res_approved, indent=2)}")

    # Test with invalid event type
    print("\n=== Testing invalid event type ===")
    event_invalid = create_mock_sqs_event(
        "invalid_event_type", test_interview_id)
    res_invalid = lambda_function.lambda_handler(
        event_invalid, {"context": True})
    print(f"Response: {json.dumps(res_invalid, indent=2)}")

    # Test direct invocation (non-SQS event)
    print("\n=== Testing direct invocation ===")
    direct_event = {"hello": "world"}
    res_direct = lambda_function.lambda_handler(
        direct_event, {"context": True})
    print(f"Response: {json.dumps(res_direct, indent=2)}")


def create_mock_sqs_event(event_type, interview_id=None):
    """
    Create a mock SQS event for testing.

    Args:
        event_type: The type of event ('interview_complete' or 'interview_approved')
        interview_id: Optional interview ID (will generate one if not provided)

    Returns:
        dict: A mock SQS event
    """
    if not interview_id:
        interview_id = str(uuid.uuid4())

    message_body = {
        "event_type": event_type,
        "interview_id": interview_id
    }

    return {
        "Records": [
            {
                "messageId": str(uuid.uuid4()),
                "receiptHandle": "mock-receipt-handle",
                "body": json.dumps(message_body),
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1523232000000",
                    "SenderId": "123456789012",
                    "ApproximateFirstReceiveTimestamp": "1523232000001"
                },
                "messageAttributes": {},
                "md5OfBody": "7b270e59b47ff90a553787216d55d91d",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-west-2:123456789012:mock-queue",
                "awsRegion": "us-east-1"
            }
        ]
    }


if __name__ == "__main__":
    main()
