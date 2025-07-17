import logging
from flask import render_template, Response

import sqs
from auth import login_required, decorate_interview_with_username, decorate_interviews_with_usernames, get_current_user_id
from shared.data.database import Database
from shared.data.data_models import InterviewStatus
from shared.events import EventType


def register_routes(app, db: Database):
    """Register reviews-related routes with the Flask app"""

    @app.route("/reviews")
    @login_required
    def reviews():
        """reviews"""

        # users can't review their own interviews
        current_user_id = get_current_user_id()

        # get reviews
        logging.info("db.get_available_reviews()")
        interviews = db.get_available_reviews(current_user_id)

        # decorate interviews with user name info from cognito
        decorate_interviews_with_usernames(interviews)

        # groups into 2 lists, one for pending and one for completed
        pending = []
        completed = []
        for interview in interviews:
            if interview.status in [InterviewStatus.PROCESSING, InterviewStatus.PENDING_REVIEW, InterviewStatus.REVIEWING]:
                pending.append(interview)
            elif interview.status in [InterviewStatus.PENDING_APPROVAL, InterviewStatus.APPROVED, InterviewStatus.REJECTED]:
                completed.append(interview)

        return render_template("reviews.html", pending=pending, completed=completed)

    @app.route("/review/start/<interview_id>")
    @login_required
    def review_start(interview_id):
        """review UI"""

        logging.info("fetching interview")
        interview = db.get_interview(interview_id)

        # update interview status to reviewing
        interview.status = InterviewStatus.REVIEWING
        db.update_interview(interview)

        # decorate interview with user name info from cognito
        decorate_interview_with_username(interview)

        return render_template("review.html", interview=interview)

    @app.route("/review/approve/<interview_id>", methods=["POST"])
    @login_required
    def review_approve(interview_id):
        """approve"""

        logging.info("fetching interview")
        interview = db.get_interview(interview_id)

        status = InterviewStatus.PENDING_APPROVAL
        logging.info(f"updating interview status to {status}")
        interview.status = status
        
        # Set approval fields
        from datetime import datetime, timezone
        interview.approved_by_user_id = get_current_user_id()
        interview.approved_on = datetime.now(timezone.utc)
        
        db.update_interview(interview)

        # post a msg to sqs to generate summary
        event_type = EventType.INTERVIEW_APPROVED.value
        logging.info(f"posting {event_type} message to SQS")
        sqs.post_message(event_type, str(interview.id))

        # redirect to reviews
        response = Response("Resource updated")
        response.headers['HX-Redirect'] = "/interviews"
        return response

    @app.route("/review/reject/<interview_id>", methods=["POST"])
    @login_required
    def review_reject(interview_id):
        """reject"""

        logging.info(f"Rejecting interview: {interview_id}")
        interview = db.get_interview(interview_id)

        if not interview:
            logging.error(f"Interview not found: {interview_id}")
            response = Response("Interview not found", status=404)
            return response

        logging.info(f"Current interview status: {interview.status}")

        # update interview status to rejected
        interview.status = InterviewStatus.REJECTED
        logging.info(f"Setting interview status to: {interview.status}")

        try:
            db.update_interview(interview)
            logging.info(f"Successfully updated interview status to rejected")
        except Exception as e:
            logging.error(f"Error updating interview: {str(e)}")
            response = Response(f"Error: {str(e)}", status=500)
            return response

        # redirect to reviews
        response = Response("Resource updated")
        response.headers['HX-Redirect'] = "/interviews"
        return response
