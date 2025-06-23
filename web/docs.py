import logging
from flask import render_template

from auth import login_required
from shared.data.database import Database
import shared.s3 as s3


def register_routes(app, db: Database):
    """Register document-related routes with the Flask app"""

    @app.route("/docs/<interview_id>")
    @login_required
    def view_document(interview_id):
        """View PDF document for an approved interview"""

        logging.info(f"Fetching document for interview {interview_id}")

        # Get the interview details
        interview = db.get_interview(interview_id)

        if not interview:
            return render_template("error.html", message="Interview not found"), 404

        try:
            # Get the S3 key for the document
            key = s3.get_interview_document_key(
                interview.topic_name, interview.id)

            # Generate a presigned URL for the PDF
            presigned_url = s3.generate_presigned_url(key)

            # Render the PDF viewer template with the presigned URL
            return render_template(
                "pdf_viewer.html",
                presigned_url=presigned_url,
                interview=interview
            )

        except Exception as e:
            logging.error(f"Error retrieving document: {str(e)}")
            return render_template("error.html", message="Could not retrieve document"), 500
