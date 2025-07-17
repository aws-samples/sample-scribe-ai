import uuid
import json
import logging
from datetime import datetime, timezone
from flask import request, render_template, current_app, current_app
from shared.data import database
from auth import login_required, admin_required, get_cognito_users, decorate_interviews_with_usernames
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from shared.data.data_models import Interview, InterviewStatus


def register_routes(app, db: database.Database):
    """Register admin-related routes with the Flask app"""

    @app.route("/admin/scopes/add")
    @login_required
    @admin_required
    def scope_add():
        """UI for new scopes"""
        return render_template("admin.scope.add.html")

    @app.route("/admin/scopes/<id>")
    @login_required
    @admin_required
    def scope_edit(id):
        """UI for editing a scope"""

        # fetch scope from database
        scope = db.get_scope(id)

        return render_template("admin.scope.edit.html", scope=scope)

    @app.route("/admin/scopes/<id>", methods=["DELETE"])
    @login_required
    @admin_required
    def scope_delete(id):
        """delete a scope"""

        logging.info(f"deleting scope {id}")
        scope = db.delete_scope(id)

        # fetch scopes from db
        scopes = db.list_scopes()

        return render_template("admin.body.html", scopes=scopes)

    @app.route("/admin/scopes/save", methods=["PUT"])
    @login_required
    @admin_required
    def scope_save():
        """save a scope"""

        name = request.form["name"]
        description = request.form["description"]

        # is this a new scope or an update?
        if "id" in request.form:
            id = request.form["id"]
            logging.info(f"updating scope {id}")
            db.update_scope(id, name, description)
        else:
            logging.info(f"creating scope {name}")
            db.create_scope(name, description, datetime.now(timezone.utc))

        # fetch scopes from db
        scopes = db.list_scopes()

        return render_template("admin.body.html", scopes=scopes)

    @app.route("/admin/scopes/cancel")
    @login_required
    @admin_required
    def scope_cancel():
        """UI for canceling a scope"""

        # fetch scopes from db
        scopes = db.list_scopes()

        return render_template("admin.body.html", scopes=scopes)

    @app.route("/admin/topics/<scope_id>")
    @login_required
    @admin_required
    def topics_list(scope_id):
        """UI for listing topics for a scope"""

        # fetch scope from database
        scope = db.get_scope(scope_id)

        # fetch topics for this scope
        topics = db.list_topics_by_scope(scope_id)

        return render_template("admin.topics.html", scope=scope, topics=topics)

    @app.route("/admin/topics/add/<scope_id>")
    @login_required
    @admin_required
    def topic_add(scope_id):
        """UI for adding a new topic to a scope"""

        # fetch scope from database
        scope = db.get_scope(scope_id)

        # fetch the list of cognito users
        users = get_cognito_users()

        return render_template(
            "admin.topic.add.html",
            scope=scope,
            users=users)

    @app.route("/admin/topics/edit/<id>")
    @login_required
    @admin_required
    def topic_edit(id):
        """UI for editing a topic"""

        # fetch topic from database
        topic = db.get_topic_by_id(id)

        # fetch the list of cognito users
        users = get_cognito_users()

        # fetch in-flight interviews for this topic
        # and add usernames to interviews
        interviews = db.get_inflight_interviews(id)
        interviews = decorate_interviews_with_usernames(interviews)

        # remove users from master list that already have in-flight interviews
        users = [user for user in users if user.id not in [
            interview.user_id for interview in interviews]]

        return render_template(
            "admin.topic.edit.html",
            topic=topic,
            users=users,
            interviews=interviews,
        )

    @app.route("/admin/topics/save", methods=["PUT"])
    @login_required
    @admin_required
    def topic_save():
        """save a topic"""

        name = request.form["name"]
        if name is None:
            name = name.strip()

        description = request.form["description"]
        if description is None:
            description = description.strip()

        scope_id = request.form["scope_id"]
        user_id = request.form["user_id"]

        # Process areas from textarea (one per line) into a list
        areas_text = request.form.get("areas", "")
        areas = [area.strip()
                 for area in areas_text.split("\n") if area.strip()]

        # does this topic already exist or is it new?
        if "id" in request.form:
            # topic exists

            # save topic
            id = request.form["id"]
            logging.info(f"updating topic {id}")
            db.update_topic(id, name, description, areas)

            # did the admin assign it to a user?
            if user_id:
                # create a new interview for the user
                # if there's not an existing one in-flight
                interview = db.get_inflight_interview_by_user_topic(user_id, id)
                if interview is None:
                    interview = Interview.new(id, user_id)
                    db.create_interview(interview)
        else:
            # new topic
            logging.info(f"creating topic {name} for scope {scope_id}")

            # create a topic
            topic = db.create_topic(
                name.strip(),
                description,
                areas,
                scope_id,
                datetime.now(timezone.utc)
            )
            id = topic["id"]

            # create an interview if topic is assigned to a user
            if user_id:
                interview = Interview.new(id, user_id)
                db.create_interview(interview)

        # fetch scope from database
        scope = db.get_scope(scope_id)

        # fetch topics for this scope
        topics = db.list_topics_by_scope(scope_id)

        return render_template("admin.topics.html", scope=scope, topics=topics)

    @app.route("/admin/topics/<id>", methods=["DELETE"])
    @login_required
    @admin_required
    def topic_delete(id):
        """delete a topic"""

        logging.info(f"deleting topic {id}")

        # Get the topic to find its scope_id before deletion
        topic = db.get_topic_by_id(id)
        if not topic:
            logging.error(f"Topic {id} not found")
            return "Topic not found", 404

        scope_id = topic["scope_id"]

        # Delete the topic
        db.delete_topic(id)

        # fetch scope from database
        scope = db.get_scope(scope_id)

        # fetch updated topics for this scope
        topics = db.list_topics_by_scope(scope_id)

        return render_template("admin.topics.html", scope=scope, topics=topics)

    @app.route("/admin")
    @login_required
    @admin_required
    def admin():
        """admin home page"""

        # fetch scopes from db
        scopes = db.list_scopes()

        return render_template("admin.html", scopes=scopes)
