import logging

from shared.data.database import Database
from shared.data.data_models import InterviewStatus
from shared.llm import orchestrator


def process(db: Database, interview_id: str):
    """
    Process an interview_complete event.

    Args:
        interview_id: The ID of the interview to process
    """
    logging.info(f"Processing interview_complete for interview {interview_id}")

    # 1. Check interview status is 'processing'
    logging.info(f"Checking interview status: {interview_id}")
    interview = db.get_interview(interview_id)
    if interview is None:
        logging.warning(f"Interview {interview_id} not found, skipping")
        return
    if interview.status != InterviewStatus.PROCESSING:
        logging.warning(
            f"Interview {interview_id} is in {interview.status} status, not in {InterviewStatus.PROCESSING} status, skipping")
        return

    # 2. Call LLM to generate interview summary
    logging.info(
        f"Calling LLM to generate summary for interview {interview_id}")
    summary = orchestrator.generate_interview_summary(
        interview.questions,
        interview.topic_name
    )
    interview.summary = summary

    # 3. Update interview status to 'pendingreview'
    interview.status = InterviewStatus.PENDING_REVIEW
    logging.info("updating interview in db")
    db.summarize_interview(interview)
    logging.info(
        f"Interview {interview_id} processed and status updated to ${InterviewStatus.PENDING_REVIEW}")
