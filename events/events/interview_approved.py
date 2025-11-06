import logging
import json
import boto3

from shared.data.database import Database
from shared.data.data_models import InterviewStatus
from shared.llm import orchestrator
from shared import s3
from shared.config import config

cognito_client = boto3.client("cognito-idp")


def process(db: Database, interview_id: str):
    """
    Process an interview_approved event.

    Args:
        interview_id: The ID of the interview to process
    """
    logging.info(f"Processing interview_approved for interview {interview_id}")

    # Check interview status
    logging.info(f"Checking interview status: {interview_id}")
    interview = db.get_interview(interview_id)
    if interview is None:
        logging.warning(f"Interview {interview_id} not found, skipping")
        return
    if interview.status != InterviewStatus.PENDING_APPROVAL:
        logging.warning(
            f"Interview {interview_id} is in {interview.status} status, not in {InterviewStatus.PENDING_APPROVAL} status, skipping")
        return

    # fetch username from cognito
    logging.info(
        f"fetching users from cognito to lookup user: {interview.user_id}")
    username = get_username(interview.user_id)

    # Call LLM to generate PDF
    logging.info(f"Calling LLM to generate PDF for interview {interview_id}")

    # generate PDF document for this interview
    pdf_bytes = orchestrator.generate_pdf(
        interview.topic_name,
        interview.questions,
        username,
    )

    # Get the S3 key for the document
    doc_key = s3.get_interview_document_key(interview.topic_name, interview.id)

    try:
        # Upload PDF to S3
        logging.info(f"writing to s3: {doc_key}")
        pdf_uri = s3.write_to_s3(
            key=doc_key,
            data=pdf_bytes,
            content_type="application/pdf",
        )

        # Create metadata for the pdf
        metadata = {
            "metadataAttributes": {
                "scope_name": interview.scope_name,
                "topic_name": interview.topic_name,
            }
        }

        # Write metadata file for KB filtering
        metadata_key = doc_key + ".metadata.json"
        logging.info(f"writing metadata to s3: {metadata_key}")
        s3.write_to_s3(
            key=metadata_key,
            data=json.dumps(metadata),
            content_type="application/json"
        )

    except Exception as e:
        logging.error(f"Error handling PDF upload: {str(e)}")
        raise e

    try:
        # now archive any existing interviews for this topic
        objects_to_archive = s3.list_objects(
            s3.get_topic_document_key(interview.topic_name))
        for obj in objects_to_archive:
            key = obj["Key"]
            # don't touch the one we just created
            if key != doc_key and key != metadata_key:
                archived_key = s3.get_archive_key(key)
                logging.info(f"archiving {key} to {archived_key}")
                s3.move_object(key, archived_key)

    except Exception as e:
        logging.error(f"Error handling document archival: {str(e)}")
        raise e

    # sync the KB datasource
    try:
        logging.info(f"Starting KB ingestion job for interview {interview_id}")
        bedrock_agent = boto3.client("bedrock-agent")
        try:
            # Get the knowledge base ID from config
            kb_id = config.knowledge_base_id
            data_source_id = config.data_source_id
            if not kb_id or not data_source_id:
                logging.warning(
                    "Knowledge base ID or data source ID not configured, skipping KB sync")
                return

            # Start the ingestion job
            logging.info(
                f"Starting ingestion job for KB: {kb_id}, data source: {data_source_id}")
            response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id
            )
            ingestion_job_id = response.get("ingestionJobId", "unknown")
            logging.info(
                f"KB ingestion job started successfully: {ingestion_job_id}")
        except Exception as e:
            logging.warning(f"Failed to start KB ingestion job: {str(e)}")

    except Exception as e:
        logging.error(f"Error starting KB ingestion job: {str(e)}")
        # Don't raise the exception here to allow the interview status update to proceed
        # This is a non-critical operation that can be retried later if needed

    # Update interview status
    interview.status = InterviewStatus.APPROVED
    logging.info("updating interview in db")
    db.update_interview(interview)
    logging.info(
        f"Interview {interview_id} processed and status updated to {InterviewStatus.APPROVED}")


def get_username(user_id: str) -> str:
    """
    Lookup username from Cognito User Pool

    Args:
        user_id: The user's Cognito sub (unique identifier)

    Returns:
        str: The username if found, or "Unknown User" if not found
    """
    try:
        # Get all users and find the one with matching user_id
        pagination_token = None

        while True:
            if pagination_token:
                response = cognito_client.list_users(
                    UserPoolId=config.cognito_pool_id,
                    AttributesToGet=["sub"],
                    PaginationToken=pagination_token
                )
            else:
                response = cognito_client.list_users(
                    UserPoolId=config.cognito_pool_id,
                    AttributesToGet=["sub"]
                )

            # Check each user in the current page
            for user in response["Users"]:
                user_attrs = {attr["Name"]: attr["Value"]
                              for attr in user["Attributes"]}
                if user_attrs.get("sub") == user_id:
                    return user["Username"]

            # Check if there are more users to fetch
            pagination_token = response.get("PaginationToken")
            if not pagination_token:
                break

        # User not found
        logging.warning(f"User with ID {user_id} not found in Cognito")
        return "Unknown User"

    except Exception as e:
        logging.error(
            f"Error fetching username from Cognito for user_id {user_id}: {str(e)}")
        return "Unknown User"
