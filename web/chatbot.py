import logging
from datetime import datetime, timezone
from flask import request, render_template, abort

import auth
from auth import login_required
from shared.log import log
from shared.data import database
from shared.llm import orchestrator


def register_routes(app, db):
    """Register chatbot-related routes with the Flask app"""

    def ask_internal(conversation, question, scope_id):
        """
        core ask implementation shared by app and api.

        Args:
            conversation: conversation object
            question: question to ask
            scope_id: scope ID to filter knowledge base results

        Returns:
            answer: answer to question
            conversation: updated conversation object
            sources: search results
        """
        # Get scope name from the database
        scope = db.get_scope(scope_id)
        if not scope:
            logging.error(f"No scope found for ID: {scope_id}")
            return "Error: Invalid scope selected", conversation, []

        scope_name = scope["name"]
        logging.info(f"Using scope: {scope_name} (ID: {scope_id})")

        # RAG orchestration to get answer
        answer, sources = orchestrator.orchestrate_chat(conversation, question, scope_name)

        # add final Q&A to conversation
        conversation["questions"].append({
            "q": question,
            "a": answer,
            "created": datetime.now(timezone.utc),
        })

        logging.info("updating conversation in db")
        log.debug(conversation)
        db.update(conversation)

        return answer, conversation, sources

    @app.route("/chat")
    @login_required
    def chat():
        """chatbot"""
        user_id = auth.get_current_user_id()
        # Get all available knowledge scopes
        scopes = db.list_scopes()
        return render_template("chatbot.html",
                               conversation={},
                               chat_history=get_chat_history(user_id),
                               scopes=scopes)

    @app.route("/new", methods=["POST"])
    @login_required
    def new():
        """POST /new starts a new conversation"""
        # Get all available knowledge scopes
        scopes = db.list_scopes()
        return render_template("chatbot.chat.html", conversation={}, scopes=scopes)

    @app.route("/ask", methods=["POST"])
    @login_required
    def ask():
        """POST /ask adds a new Q&A to the conversation"""

        # get conversation id and question from form
        if "conversation_id" not in request.values:
            m = "missing required form data: conversation_id"
            logging.error(m)
            abort(400, m)
        id = request.values["conversation_id"]
        logging.info(f"conversation id: {id}")

        if "question" not in request.values:
            m = "missing required form data: question"
            logging.error(m)
            abort(400, m)
        question = request.values["question"]
        question = question.rstrip()
        logging.info(f"question: {question}")

        # Get scope_id - it's now required
        if "scope_id" not in request.values or not request.values["scope_id"]:
            m = "missing required form data: scope_id"
            logging.error(m)
            abort(400, m)

        scope_id = request.values.get("scope_id")
        logging.info(f"scope_id: {scope_id}")

        user_id = auth.get_current_user_id()

        # if conversation id is blank, start a new one
        # else, fetch conversation history from db
        if id == "":
            conversation = db.new_chat(
                user_id, datetime.now(timezone.utc).isoformat(), scope_id)
        else:
            conversation = db.get(id)
            # Update scope_id if it changed
            if conversation.get("scope_id") != scope_id:
                conversation["scope_id"] = scope_id
            logging.info("fetched conversation")
            log.debug(conversation)

        _, conversation, sources = ask_internal(conversation, question, scope_id)

        # Get all available knowledge scopes for the dropdown
        scopes = db.list_scopes()

        # render ui with question history, answer, and top 3 document references
        return render_template("chatbot.body.html",
                               conversation=conversation,
                               sources=sources,
                               chat_history=get_chat_history(user_id),
                               scopes=scopes)

    @app.route("/conversation/<id>", methods=["GET"])
    @login_required
    def get_conversation(id):
        """GET /conversation/<id> fetches a conversation by id"""

        conversation = db.get(id)
        # Get all available knowledge scopes
        scopes = db.list_scopes()
        return render_template("chatbot.chat.html", conversation=conversation, scopes=scopes)

    # @app.route("/begin", methods=["POST"])
    # @login_required
    # def begin():
    #     """POST /begin begins a conversation"""

    #     question = request.values["question"]
    #     question = question.strip()
    #     logging.info(f"question: {question}")

    #     user_id = auth.get_current_user_id()

    #     # if conversation id is blank, start a new one
    #     # else, fetch conversation history from db
    #     conversation = db.new(user_id, datetime.now(timezone.utc).isoformat())

    #     answer, conversation = ask_internal(conversation, question)

    #     # render ui with question history, answer, and top 3 document references
    #     return render_template("body.html",
    #                            conversation=conversation,
    #                            chat_history=get_chat_history(user_id))

    def get_chat_history(user_id):
        """
        fetches the user's latest chat history
        """
        logging.info(f"fetching chat history for user {user_id}")

        # fetch last 10 questions from db
        history = db.list_by_user(user_id, 10)

        # build list of objects that have
        # the first question in each conversation and the date
        result = []
        for h in history:
            if len(h["questions"]) == 0:
                continue
            result.append({
                "conversationId": h["conversationId"],
                "created": datetime.fromisoformat(h["created"]).strftime("%B %d, %Y"),
                "initial_question": h["questions"][0]["q"],
            })
        return result
