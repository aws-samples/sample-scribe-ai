import logging
from datetime import datetime, timezone
from flask import request, render_template, abort, Response

from auth import get_current_user_id, login_required, decorate_interview_with_username, decorate_interviews_with_usernames, is_admin
import sqs
from shared.data.database import Database
from shared.data.data_models import InterviewStatus
from shared.llm import orchestrator
from shared.events import EventType


def _complete_interview(interview, db):
    """Shared function to complete an interview and trigger summary generation"""
    status = InterviewStatus.PROCESSING
    logging.info(f"updating interview status in db to {status}")
    interview.completed = datetime.now(timezone.utc)
    interview.status = status
    db.end_interview(interview)

    # post a msg to sqs to generate summary
    event_type = EventType.INTERVIEW_COMPLETE.value
    logging.info(f"posting {event_type} message to SQS")
    sqs.post_message(event_type, str(interview.id))


def register_routes(app, db: Database):
    """Register interview-related routes with the Flask app"""

    @app.route("/interviews")
    @login_required
    def interviews():
        """interviews"""

        # get interviews for this user
        user_id = get_current_user_id()
        logging.info(f"fetching interviews for user {user_id}")
        assigned = db.get_available_interviews(user_id)

        # get reviews available to this user
        reviews = db.get_available_reviews(user_id)
        reviews = decorate_interviews_with_usernames(reviews)

        # Initialize all as an empty list by default
        all = []

        # if the user's an admin, fetch all interviews
        if is_admin():
            all = db.list_interviews(100)
            all = decorate_interviews_with_usernames(all)

            # whether or not an interview is "viewable"
            for interview in all:
                interview.viewable = False
                if (interview.status == InterviewStatus.NOT_STARTED or
                        interview.status == InterviewStatus.STARTED) == False:
                    interview.viewable = True

        # Query talk mode enabled status from database with graceful degradation
        try:
            talk_mode_enabled = db.get_talk_mode_enabled()
        except Exception as e:
            logging.error(
                f"Error retrieving talk mode setting in interviews: {e}")
            # Default to enabled for backward compatibility
            talk_mode_enabled = True

        return render_template("interviews.html",
                               assigned=assigned,
                               reviews=reviews,
                               all=all,
                               talk_mode_enabled=talk_mode_enabled,
                               )

    @app.route("/interviews/view/<id>")
    @login_required
    def view_interview(id):
        """View a completed interview in read-only mode"""

        # get interview
        interview = db.get_interview(id)
        if not interview:
            abort(404, "Interview not found")

        # decorate interview with user name info from cognito
        decorate_interview_with_username(interview)

        logging.info(f"Viewing interview {id}")
        return render_template("interviews.view.html", interview=interview)

    @app.route("/interviews/start/<id>")
    @login_required
    def start_interview(id):
        """interviews"""

        # get interview
        interview = db.get_interview(id)

        # kick off interview by invoking llm with prompt
        logging.info("orchestrator.start_interview()")
        ai_question = orchestrator.start_interview(
            interview.topic_name,
            interview.topic_areas
        )
        interview.add_question(ai_question)

        # update interview to started
        logging.info("db.update_interview()")
        interview.status = InterviewStatus.STARTED
        db.update_interview(interview)

        logging.info("rendering interviews.conversation.body.html")
        return render_template("interviews.conversation.body.html", interview=interview)

    @app.route("/interviews/resume/<id>")
    @login_required
    def resume_interview(id):
        """resume interviews"""

        # get interview
        interview = db.get_interview(id)

        logging.info("rendering interviews.conversation.body.html")
        return render_template("interviews.conversation.body.html", interview=interview)

    @app.route("/interviews/voice/<id>")
    @login_required
    def voice_interview(id):
        """Start or resume a voice interview"""

        # get interview
        interview = db.get_interview(id)
        if not interview:
            abort(404, "Interview not found")

        # Check if user has access to this interview
        user_id = get_current_user_id()
        if interview.user_id != user_id:
            abort(403, "Access denied to this interview")

        # decorate interview with user name info from cognito
        decorate_interview_with_username(interview)

        logging.info(f"Rendering voice interview page for interview {id}")
        return render_template("interviews.voice.html", interview=interview)

    @app.route("/interview/answer", methods=["POST"])
    @login_required
    def interview_answer():
        """POST /answer adds a new Q&A to the interview"""

        # get interview id and answer from form
        if "interview_id" not in request.values:
            m = "missing required form data: interview_id"
            logging.error(m)
            abort(400, m)
        id = request.values["interview_id"]
        logging.info(f"interview id: {id}")

        if "answer" not in request.values:
            m = "missing required form data: question"
            logging.error(m)
            abort(400, m)
        answer = request.values["answer"]
        answer = answer.rstrip()
        logging.info(f"answer: {answer}")

        interview = db.get_interview(id)
        logging.info("fetched interview")

        # at this point we have a interview question with ai question
        # update the latest question with the user's answer
        question = interview.questions[-1]
        question.answer = answer

        # ask the ai for a new question
        new_question = orchestrator.orchestrate_answer(
            interview.questions,
            interview.topic_name,
            interview.topic_areas,
        )

        # add new question to interview
        interview.add_question(new_question)

        logging.info("updating interview in db")
        db.update_interview(interview)

        # render ui
        return render_template("interviews.conversation.body.html",
                               interview=interview)
        #    chat_history=get_interview_history(user_id))

    @app.route("/interview/end", methods=["PUT"])
    @login_required
    def interview_end():
        """ends an the interview"""

        # get interview id and answer from form
        if "interview_id" not in request.values:
            m = "missing required form data: interview_id"
            logging.error(m)
            abort(400, m)
        id = request.values["interview_id"]

        logging.info(f"interview id: {id}")
        interview = db.get_interview(id)
        logging.info("fetched interview")

        _complete_interview(interview, db)

        # Create a response with the HX-Redirect header
        response = Response("Resource updated")
        response.headers['HX-Redirect'] = "/interviews"
        return response

    def get_interview_history(user_id):
        """
        fetches the user's latest interview history
        """
        logging.info(f"fetching interview history for user {user_id}")

        # fetch last 10 questions from db
        history = db.list_interviews_by_user(user_id, 10)

        # build list of objects that have
        # the first question in each interview and the date
        result = []
        for h in history:
            if len(h["questions"]) == 0:
                continue
            result.append({
                "interviewId": h["interviewId"],
                "created": datetime.fromisoformat(h["created"]).strftime("%B %d, %Y"),
                "initial_question": h["questions"][0]["q"],
            })
        return result
