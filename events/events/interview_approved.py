import logging
import json

from shared.data.database import Database
from shared.data.data_models import InterviewStatus
from shared.llm import orchestrator
from shared import s3


def process(db: Database, interview_id: str):
    """
    Process an interview_approved event.

    Args:
        interview_id: The ID of the interview to process
    """
    logging.info(f"Processing interview_approved for interview {interview_id}")

    # 1. Check interview status
    logging.info(f"Checking interview status: {interview_id}")
    interview = db.get_interview(interview_id)
    if interview is None:
        logging.warning(f"Interview {interview_id} not found, skipping")
        return
    if interview.status != InterviewStatus.PENDING_APPROVAL:
        logging.warning(
            f"Interview {interview_id} is in {interview.status} status, not in {InterviewStatus.PENDING_APPROVAL} status, skipping")
        return

    # 2. Call LLM to generate PDF
    logging.info(f"Calling LLM to generate PDF for interview {interview_id}")

    # generate PDF document for this interview
    pdf_bytes = orchestrator.generate_pdf(
        interview.topic_name,
        interview.questions
    )

    # Get the S3 key for the document
    key = s3.get_interview_document_key(interview.topic_name, interview.id)

    try:
        # Upload PDF to S3
        logging.info(f"writing to s3: {key}")
        pdf_uri = s3.write_to_s3(
            key=key,
            data=pdf_bytes,
            content_type='application/pdf',
        )

        # Create metadata for the pdf
        metadata = {
            "metadataAttributes": {
                "scope_name": interview.scope_name,
                "topic_name": interview.topic_name,
            }
        }

        # Write metadata file for KB filtering
        key = key + ".metadata.json"
        logging.info(f"writing to s3: {key}")
        s3.write_to_s3(
            key=key,
            data=json.dumps(metadata),
            content_type='application/json'
        )

    except Exception as e:
        logging.error(f"Error handling PDF upload: {str(e)}")
        raise e

    # 3. Update interview status
    interview.status = InterviewStatus.APPROVED
    logging.info("updating interview in db")
    db.update_interview(interview)
    logging.info(
        f"Interview {interview_id} processed and status updated to {InterviewStatus.APPROVED}")
