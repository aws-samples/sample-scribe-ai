import boto3
import logging
import json
from typing import Union, Dict, Any, List
from botocore.exceptions import ClientError

from shared.config import config

s3_client = boto3.client('s3')

KB_KEY = "kb"
ARCHIVE_KEY = "archived"


def get_topic_document_key(topic_name: str) -> str:
    """
    Generate the S3 key for an interview topic.

    Args:
        topic_name: The name of the interview topic

    Returns:
        str: The S3 key path for the document
    """
    sanitized_topic = topic_name.strip().replace(" ", "-").lower()
    return f"{KB_KEY}/{sanitized_topic}/"


def get_interview_document_key(topic_name: str, interview_id: str) -> str:
    """
    Generate the S3 key for an interview document based on topic name and interview ID.

    Args:
        topic_name: The name of the interview topic
        interview_id: The unique identifier for the interview

    Returns:
        str: The S3 key path for the document
    """
    return get_topic_document_key(topic_name) + f"{interview_id}.pdf"


def get_archive_key(key: str) -> str:
    """
    Get archive key for active key
    """
    return key.replace(f"{KB_KEY}/", f"{ARCHIVE_KEY}/")


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


def list_objects(
    prefix: str = '',
    bucket_name: str = None,
    max_keys: int = 1000,
    delimiter: str = None
) -> List[Dict[str, Any]]:
    """
    List objects in an S3 bucket with optional prefix filtering.

    Args:
        prefix: Filter objects by prefix (default: empty string for all objects)
        bucket_name: The S3 bucket name (if None, will use config.s3_bucket_name)
        max_keys: Maximum number of objects to return (default: 1000, max: 1000)
        delimiter: Delimiter to use for grouping keys (e.g., '/' for folder-like structure)

    Returns:
        List[Dict[str, Any]]: List of object metadata dictionaries containing:
            - Key: The object key (path/filename)
            - LastModified: When the object was last modified
            - ETag: The entity tag of the object
            - Size: Size of the object in bytes
            - StorageClass: The storage class of the object

    Raises:
        ClientError: If there's an error accessing the S3 bucket
        ValueError: If bucket_name cannot be determined
    """
    try:
        # Determine the bucket name
        if not bucket_name:
            bucket_name = config.s3_bucket_name

        if not bucket_name:
            raise ValueError(
                "No S3 bucket specified and S3_BUCKET_NAME not found in configuration")

        # Validate max_keys
        if max_keys > 1000:
            max_keys = 1000
            logging.warning("max_keys reduced to 1000 (AWS S3 limit)")

        # Prepare list_objects_v2 parameters
        list_params = {
            'Bucket': bucket_name,
            'MaxKeys': max_keys
        }

        if prefix:
            list_params['Prefix'] = prefix

        if delimiter:
            list_params['Delimiter'] = delimiter

        # List objects
        response = s3_client.list_objects_v2(**list_params)

        # Extract object information
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                objects.append({
                    'Key': obj['Key'],
                    'LastModified': obj['LastModified'],
                    'ETag': obj['ETag'].strip('"'),  # Remove quotes from ETag
                    'Size': obj['Size'],
                    'StorageClass': obj.get('StorageClass', 'STANDARD')
                })

        logging.info(
            f"Listed {len(objects)} objects from s3://{bucket_name}/{prefix}")
        return objects

    except ClientError as e:
        logging.error(
            f"Error listing objects from S3 bucket {bucket_name}: {str(e)}")
        raise


def list_objects_paginated(
    prefix: str = '',
    bucket_name: str = None,
    page_size: int = 1000,
    delimiter: str = None
) -> List[Dict[str, Any]]:
    """
    List all objects in an S3 bucket with pagination support for large buckets.

    Args:
        prefix: Filter objects by prefix (default: empty string for all objects)
        bucket_name: The S3 bucket name (if None, will use config.s3_bucket_name)
        page_size: Number of objects to fetch per page (default: 1000, max: 1000)
        delimiter: Delimiter to use for grouping keys (e.g., '/' for folder-like structure)

    Returns:
        List[Dict[str, Any]]: List of all object metadata dictionaries

    Raises:
        ClientError: If there's an error accessing the S3 bucket
        ValueError: If bucket_name cannot be determined
    """
    try:
        # Determine the bucket name
        if not bucket_name:
            bucket_name = config.s3_bucket_name

        if not bucket_name:
            raise ValueError(
                "No S3 bucket specified and S3_BUCKET_NAME not found in configuration")

        # Validate page_size
        if page_size > 1000:
            page_size = 1000
            logging.warning("page_size reduced to 1000 (AWS S3 limit)")

        all_objects = []
        continuation_token = None

        while True:
            # Prepare list_objects_v2 parameters
            list_params = {
                'Bucket': bucket_name,
                'MaxKeys': page_size
            }

            if prefix:
                list_params['Prefix'] = prefix

            if delimiter:
                list_params['Delimiter'] = delimiter

            if continuation_token:
                list_params['ContinuationToken'] = continuation_token

            # List objects
            response = s3_client.list_objects_v2(**list_params)

            # Extract object information
            if 'Contents' in response:
                for obj in response['Contents']:
                    all_objects.append({
                        'Key': obj['Key'],
                        'LastModified': obj['LastModified'],
                        # Remove quotes from ETag
                        'ETag': obj['ETag'].strip('"'),
                        'Size': obj['Size'],
                        'StorageClass': obj.get('StorageClass', 'STANDARD')
                    })

            # Check if there are more objects to fetch
            if response.get('IsTruncated', False):
                continuation_token = response.get('NextContinuationToken')
            else:
                break

        logging.info(
            f"Listed {len(all_objects)} objects from s3://{bucket_name}/{prefix}")
        return all_objects

    except ClientError as e:
        logging.error(
            f"Error listing objects from S3 bucket {bucket_name}: {str(e)}")
        raise


def move_object(src: str, dest: str) -> None:
    """
    Move an object from one S3 location to another by copying and deleting the original.
    Uses server-side copy for efficiency.
    """
    bucket = config.s3_bucket_name

    # Server-side copy (no data transfer through client)
    s3_client.copy_object(
        CopySource={'Bucket': bucket, 'Key': src},
        Bucket=bucket,
        Key=dest
    )

    # Delete original
    s3_client.delete_object(Bucket=bucket, Key=src)
