import logging
import json
import uuid
from datetime import datetime, timezone
from flask import request, abort, jsonify, Response, session
import boto3
from botocore.exceptions import ClientError

import chatbot
from auth import login_required, get_current_user_id
from shared.log import log
from shared.llm import bedrock_kb, orchestrator
from shared.data.database import Database
from shared.data.data_models import InterviewStatus
from shared.config import config
from interviews import _complete_interview


def register_routes(app, db: Database):
    """Register API routes with the Flask app"""

    # Initialize AWS Lambda client for voice routes
    lambda_client = boto3.client('lambda')

    @app.route("/api/ask", methods=["POST"])
    @login_required
    def ask_api_new():
        """returns an answer to a question in a new conversation"""

        # get request json from body
        body = request.get_json()
        log.debug(body)
        if "question" not in body:
            m = "missing field: question"
            logging.error(m)
            abort(400, m)
        question = body["question"]

        conversation = db.new(datetime.now(timezone.utc))

        answer, conversation = chatbot.ask_internal(conversation, question)

        return {
            "conversationId": conversation["conversationId"],
            "answer": answer,
        }

    @app.route("/api/ask/<id>", methods=["POST"])
    @login_required
    def ask_api(id):
        """returns an answer to a question in a conversation"""

        # get request json from body
        body = request.get_json()
        log.debug(body)
        if "question" not in body:
            m = "missing field: question"
            logging.error(m)
            abort(400, m)
        question = body["question"]

        if id == "":
            m = "conversation id is required"
            logging.error(m)
            abort(400, m)
        else:
            conversation = db.get(id)
            logging.info("fetched conversation")
            log.debug(conversation)

        answer, _ = chatbot.ask_internal(conversation, question)

        return {
            "conversationId": id,
            "answer": answer,
        }

    @app.route("/api/conversations")
    @login_required
    def conversations_list():
        """fetch top 10 conversations"""
        return db.list(10)

    @app.route("/api/conversations/users/<user_id>")
    @login_required
    def conversations_get_by_user(user_id):
        """fetch top 10 conversations for a user"""
        return db.list_by_user(user_id, 10)

    @app.route("/api/conversations/<id>")
    @login_required
    def conversations_get(id):
        """fetch a conversation by id"""
        return db.get(id)

    @app.route("/api/interviews")
    @login_required
    def interviews_list():
        """fetch top 10 interviews"""
        return db.list_interviews(10)

    @app.route("/api/search", methods=["POST"])
    @login_required
    def search():
        """
        Search the Bedrock Knowledge Base directly.

        Request body:
        {
            "query": "search query text",
            "scope_id": "uuid-of-scope",
            "result_count": 5  # optional, defaults to 5
        }
        """
        try:
            data = request.json

            if not data or 'query' not in data or 'scope_id' not in data:
                return jsonify({'error': 'Missing required parameters: query and scope_id'}), 400

            query = data['query']
            scope_id = data['scope_id']
            result_count = data.get('result_count', 5)

            # Get the scope name from the database using scope_id
            scope = db.get_scope(scope_id)
            if not scope:
                return jsonify({'error': f'Scope with ID {scope_id} not found'}), 404

            scope_name = scope['name']

            # Query the Bedrock Knowledge Base using the existing function
            relevant_docs = bedrock_kb.get_relevant_docs(
                query=query,
                top_k=result_count,
                scope_name=scope_name
            )

            # Process and return the search results
            results = []
            for doc in relevant_docs:
                content = ""
                if "text" in doc.get("content", {}):
                    content = doc["content"]["text"]

                source = ""
                if doc.get("location", {}).get("type") == "S3" and "uri" in doc.get("location", {}).get("s3Location", {}):
                    source = doc["location"]["s3Location"]["uri"]

                results.append({
                    'content': content,
                    'source': source,
                    'score': doc.get('score', 0)
                })

            return jsonify({
                'query': query,
                'scope_name': scope_name,
                'results': results
            })

        except Exception as e:
            app.logger.error(f"Error in search API: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route("/api/scopes", methods=["GET"])
    @login_required
    def get_scopes():
        """
        Get all available knowledge scopes from the database.
        """
        try:
            scopes = db.list_scopes()

            # Format the response
            formatted_scopes = []
            for scope in scopes:
                formatted_scopes.append({
                    'id': scope['id'],
                    'name': scope['name'],
                    'description': scope['description'],
                    'created': scope['created'].isoformat() if scope['created'] else None
                })

            return jsonify({'scopes': formatted_scopes})

        except Exception as e:
            app.logger.error(f"Error in get_scopes API: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route("/api/topics", methods=["GET"])
    @login_required
    def get_topics():
        """
        Get all available topics, optionally filtered by scope_id.

        Query parameters:
        - scope_id: Optional UUID to filter topics by scope
        """
        try:
            scope_id = request.args.get('scope_id')

            if scope_id:
                # Get topics for a specific scope
                topics = db.list_topics_by_scope(scope_id)
            else:
                # Get all topics from all scopes
                # Since there's no direct method for this, we'll get all scopes and then get topics for each
                scopes = db.list_scopes()
                topics = []
                for scope in scopes:
                    scope_topics = db.list_topics_by_scope(scope['id'])
                    for topic in scope_topics:
                        # Add scope information to each topic
                        topic['scope_name'] = scope['name']
                        topic['scope_id'] = scope['id']
                    topics.extend(scope_topics)

            # Format the response
            formatted_topics = []
            for topic in topics:
                formatted_topics.append({
                    'id': topic['id'],
                    'name': topic['name'],
                    'description': topic['description'],
                    'areas': topic['areas'] if 'areas' in topic else [],
                    'scope_id': topic.get('scope_id'),
                    'scope_name': topic.get('scope_name'),
                    'created': topic['created'].isoformat() if topic['created'] else None
                })

            return jsonify({'topics': formatted_topics})

        except Exception as e:
            app.logger.error(f"Error in get_topics API: {str(e)}")
            return jsonify({'error': str(e)}), 500

    # Voice Interview API Routes
    @app.route("/api/interviews/<interview_id>/voice/start", methods=["POST"])
    @login_required
    def start_voice_interview(interview_id):
        """Initialize a voice interview session"""
        try:
            user_id = get_current_user_id()
            if not user_id:
                abort(401, "User not authenticated")

            interview = db.get_interview(interview_id)
            if not interview:
                abort(404, "Interview not found")

            if interview.user_id != user_id:
                abort(403, "Access denied to this interview")

            if interview.status not in [InterviewStatus.NOT_STARTED, InterviewStatus.STARTED]:
                abort(
                    400, f"Interview cannot be started in voice mode. Current status: {interview.status.value}")

            session_id = str(uuid.uuid4())
            voice_session_metadata = {
                "session_id": session_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "status": "initializing",
                "voice_id": "matthew",
            }

            interview.voice_mode = True
            interview.voice_session_metadata = voice_session_metadata

            if interview.status == InterviewStatus.NOT_STARTED:
                interview.status = InterviewStatus.STARTED

            db.update_interview(interview)

            topic_areas = f"- {interview.topic_areas[0]}"
            for area in interview.topic_areas[1:]:
                topic_areas += f"\n- {area}"

            # Get the voice interview prompt from Bedrock
            voice_prompt = orchestrator.get_prompt(
                config.prompt_interview_voice)
            system_prompt = voice_prompt.replace(
                "{{topic}}", interview.topic_name)
            system_prompt = system_prompt.replace("{{areas}}", topic_areas)

            lambda_payload = {
                "eventType": "session-start",
                "userId": user_id,
                "interviewId": interview_id,
                "sessionId": voice_session_metadata["session_id"],
                "voiceId": voice_session_metadata["voice_id"],
                "topicAreas": interview.topic_areas,
                "systemPrompt": system_prompt,
            }

            function_name = config.voice_lambda_function_name
            logging.info(f"Invoking voice Lambda function: {function_name}")
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',
                Payload=json.dumps(lambda_payload)
            )

            logging.info(
                f"Voice Lambda invoked successfully. Status: {response['StatusCode']}")

            voice_session_metadata['status'] = 'active'
            interview.voice_session_metadata = voice_session_metadata
            db.update_interview(interview)

            return jsonify({
                "session_id": session_id,
                "interview_id": interview_id,
                "status": "active",
                "appsync_channel": f"/nova-sonic-voice/user/{user_id}/{session_id}",
                "appsync_endpoint": config.appsync_events_endpoint,
                "message": "Voice session started successfully"
            })

        except ClientError as e:
            logging.error(f"AWS error starting voice session: {str(e)}")
            return jsonify({'error': 'Failed to start voice session'}), 500
        except Exception as e:
            logging.error(f"Error starting voice session: {str(e)}")
            return jsonify({'error': 'Failed to start voice session'}), 500

    @app.route("/api/interviews/<interview_id>/voice/end", methods=["PUT"])
    @login_required
    def end_voice_interview(interview_id):
        """End a voice interview session and complete the interview"""
        try:
            user_id = get_current_user_id()
            if not user_id:
                abort(401, "User not authenticated")

            interview = db.get_interview(interview_id)
            if not interview:
                abort(404, "Interview not found")

            if interview.user_id != user_id:
                abort(403, "Access denied to this interview")

            if not interview.voice_mode:
                abort(400, "Interview is not in voice mode")

            voice_session_metadata = interview.voice_session_metadata or {}
            session_id = voice_session_metadata.get('session_id')

            if not session_id:
                abort(400, "No active voice session found")

            voice_session_metadata.update({
                'status': 'stopped',
                'stopped_at': datetime.now(timezone.utc).isoformat()
            })
            interview.voice_session_metadata = voice_session_metadata
            db.update_interview(interview)

            _complete_interview(interview, db)

            return jsonify({
                'session_id': session_id,
                'interview_id': interview_id,
                'status': 'completed',
                'message': 'Voice interview ended successfully'
            })

        except ClientError as e:
            logging.error(f"AWS error ending voice interview: {str(e)}")
            return jsonify({'error': 'Failed to end voice interview'}), 500
        except Exception as e:
            logging.error(f"Error ending voice interview: {str(e)}")
            return jsonify({'error': 'Failed to end voice interview'}), 500

    @app.route("/api/cognito-token", methods=["GET"])
    @login_required
    def get_cognito_token():
        """Get AWS Cognito access token for AppSync Events authentication"""
        try:
            access_token = session.get('cognito_access_token')

            if not access_token:
                return jsonify({
                    'error': 'No Cognito access token available',
                    'message': 'Please re-authenticate'
                }), 401

            return jsonify({
                'accessToken': access_token
            })

        except Exception as e:
            logging.error(f"Error getting Cognito token: {str(e)}")
            return jsonify({'error': 'Failed to get authentication token'}), 500
