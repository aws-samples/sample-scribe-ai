import logging
from flask import render_template, request
from auth import login_required, decorate_interview_with_username, get_user_by_id
from shared.data.database import Database


def register_routes(app, db: Database):
    """Register kb-related routes with the Flask app"""

    @app.route("/kb")
    @login_required
    def kb():
        """knowledge base"""
        logging.info("fetching scopes")
        scopes = db.list_scopes()
        topics = []
        has_selected_scope = False

        # default to 1st scope
        if len(scopes) > 0:
            scope_id = scopes[0]["id"]
            topics = _get_kb_topics(scope_id)
            has_selected_scope = True

        return render_template("kb.html", scopes=scopes, topics=topics, has_selected_scope=has_selected_scope)

    @app.route("/kb/topics")
    @login_required
    def kb_scope_changed():
        """Get approved topics for scope"""
        scope_id = request.args.get("scope_id")
        topics = _get_kb_topics(scope_id)
        has_selected_scope = scope_id is not None and scope_id != ""

        return render_template("kb.topics.html", topics=topics, has_selected_scope=has_selected_scope)

    def _get_kb_topics(scope_id):
        """Get approved topics for scope"""

        logging.info(f"fetching topics for scope {scope_id}")
        topics = db.list_topics_by_scope(scope_id)

        # for each topic, get the latest approved interview
        for topic in topics:
            logging.info(
                f"fetching latest approved interview for {topic["id"]}")
            interview = db.get_latest_approved_interview(topic["id"])
            if interview:
                # Decorate with both interviewer and approver usernames
                interview = decorate_interview_with_username(interview)
                
                # Add approver username if approved_by_user_id exists
                if interview.approved_by_user_id:
                    try:
                        approver_user = get_user_by_id(interview.approved_by_user_id)
                        if approver_user:
                            interview.approved_by_user_name = approver_user.username
                        else:
                            interview.approved_by_user_name = "Unknown User"
                    except Exception as e:
                        logging.warning(f"Could not fetch approver user info: {e}")
                        interview.approved_by_user_name = "Unknown User"
                else:
                    interview.approved_by_user_name = None
                    
                topic["interview"] = interview

        return topics
