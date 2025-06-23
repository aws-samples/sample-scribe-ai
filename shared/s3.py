import boto3
import logging
from typing import Union, Dict, Any
from botocore.exceptions import ClientError

from shared.config import config

s3_client = boto3.client('s3')


def get_interview_document_key(topic_name: str, interview_id: str) -> str:
    """
    Generate the S3 key for an interview document based on topic name and interview ID.

    Args:
        topic_name: The name of the interview topic
        interview_id: The unique identifier for the interview

    Returns:
        str: The S3 key path for the document
    """
    sanitized_name = topic_name.strip().replace(" ", "-").lower()
    return f"interviews/{sanitized_name}/{interview_id}.pdf"


def generate_presigned_url(key: str, bucket_name: str = None, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for accessing an S3 object.

    Args:
        key: The S3 object key (path/filename)
        bucket_name: The S3 bucket name (if None, will use config.s3_bucket_name)
        expires_in: URL expiration time in seconds (default: 1 hour)

    Returns:
        str: The presigned URL for accessing the object

    Raises:
        ClientError: If there's an error generating the presigned URL
        ValueError: If bucket_name cannot be determined
    """
    try:
        # Determine the bucket name
        if not bucket_name:
            bucket_name = config.s3_bucket_name

        if not bucket_name:
            raise ValueError(
                "No S3 bucket specified and S3_BUCKET_NAME not found in configuration")

        # Generate the presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=expires_in
        )

        return presigned_url

    except ClientError as e:
        logging.error(f"Error generating presigned URL for {key}: {str(e)}")
        raise


def write_to_s3(
    data: Union[bytes, str, Dict[Any, Any]],
    key: str,
    content_type: str = None,
    bucket_name: str = None,
    metadata: Dict[str, str] = None
) -> str:
    """
    Write data to an S3 bucket with the specified key and content type.

    Args:
        data: The data to write (bytes, string, or dict that will be converted to JSON)
        key: The S3 object key (path/filename)
        content_type: The MIME type of the content (e.g., 'application/pdf', 'application/json')
        bucket_name: The S3 bucket name (if None, will use config.s3_bucket_name)
        metadata: Optional metadata to attach to the S3 object

    Returns:
        str: The S3 URI of the uploaded object (s3://bucket-name/key)

    Raises:
        Exception: If bucket_name cannot be determined or upload fails
    """
    try:
        # Determine the bucket name
        if not bucket_name:
            bucket_name = config.s3_bucket_name

        if not bucket_name:
            raise ValueError(
                "No S3 bucket specified and S3_BUCKET_NAME not found in configuration")

        # Prepare the data based on its type
        if isinstance(data, dict):
            import json
            data = json.dumps(data)
            if not content_type:
                content_type = 'application/json'

        # Convert string to bytes if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
            if not content_type:
                content_type = 'text/plain'

        # Set default content type for bytes if not specified
        if not content_type and isinstance(data, bytes):
            content_type = 'application/octet-stream'

        # Upload to S3
        put_args = {
            'Bucket': bucket_name,
            'Key': key,
            'Body': data
        }

        if content_type:
            put_args['ContentType'] = content_type

        if metadata:
            put_args['Metadata'] = metadata

        s3_client.put_object(**put_args)

        s3_uri = f"s3://{bucket_name}/{key}"
        logging.info(f"Successfully uploaded to {s3_uri}")
        return s3_uri

    except Exception as e:
        logging.error(f"Error uploading to S3: {str(e)}")
        raise
