import os
import uuid
import logging
import json
import time
import threading
import psycopg
import boto3
from datetime import datetime, timezone
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

from shared.config import config
from shared.data.data_models import InterviewRecord, Interview, InterviewStatus

PsycopgInstrumentor().instrument()
secrets_manager = boto3.client("secretsmanager")


class CredentialCache:
    """Thread-safe cache for database credentials"""

    def __init__(self, ttl_seconds=3600):  # Default TTL: 1 hour
        self.username = None
        self.password = None
        self.last_refresh = 0
        self.ttl_seconds = ttl_seconds
        self.lock = threading.RLock()  # Reentrant lock for thread safety

    def is_valid(self):
        """Check if cached credentials are still valid"""
        with self.lock:
            if not self.username or not self.password:
                return False
            current_time = time.time()
            return (current_time - self.last_refresh) < self.ttl_seconds

    def update(self, username, password):
        """Update cached credentials in a thread-safe manner"""
        with self.lock:
            self.username = username
            self.password = password
            self.last_refresh = time.time()

    def get_credentials(self):
        """Get current credentials in a thread-safe manner"""
        with self.lock:
            return (self.username, self.password)


class Database():
    """Encapsulate database access"""

    # Class-level credential cache shared across all instances
    _credential_cache = CredentialCache()
    # Lock for synchronizing credential refresh operations
    _refresh_lock = threading.Lock()

    def __init__(self):
        self.host = config.postgres_host
        self.dbname = config.postgres_dbname
        self.user = config.postgres_user
        self.password = config.postgres_password
        self.secret_arn = config.postgres_secret_arn

    def connect(self):
        # If running in AWS, use cached credentials or fetch from secrets manager
        if self.secret_arn is not None:
            # Use cached credentials if they're still valid
            if Database._credential_cache.is_valid():
                self.user, self.password = Database._credential_cache.get_credentials()
                logging.debug("using cached database credentials")
            else:
                # Use a lock to ensure only one thread refreshes the credentials at a time
                with Database._refresh_lock:
                    # Check again in case another thread refreshed while we were waiting
                    if not Database._credential_cache.is_valid():
                        logging.debug(
                            "fetching database credentials from secrets manager")
                        try:
                            secret = secrets_manager.get_secret_value(
                                SecretId=self.secret_arn)
                            creds = json.loads(secret["SecretString"])
                            logging.debug("secret successfully fetched")
                            self.user = creds["username"]
                            self.password = creds["password"]
                            # Update the cache
                            Database._credential_cache.update(
                                self.user, self.password)
                        except Exception as e:
                            logging.error(f"Error fetching credentials: {e}")
                            # If we can't refresh, but have old credentials, use them
                            if Database._credential_cache.username and Database._credential_cache.password:
                                self.user, self.password = Database._credential_cache.get_credentials()
                                logging.warning(
                                    "Using expired credentials due to refresh failure")
                            else:
                                # No choice but to raise the exception
                                raise
                    else:
                        # Another thread refreshed the credentials while we were waiting
                        self.user, self.password = Database._credential_cache.get_credentials()

        return psycopg.connect(
            host=self.host,
            dbname=self.dbname,
            user=self.user,
            password=self.password
        )

    def new_chat(self, user_id, created, scope_id=None):
        """creates a new conversation"""

        id = str(uuid.uuid4())

        conversation = {
            "conversationId": id,
            "userId": user_id,
            "created": created,
            "scope_id": scope_id,
            "questions": []
        }

        query = """
            INSERT INTO conversation (id, created, scope_id, user_id, data, summary)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (id, created, scope_id, user_id,
                  json.dumps(conversation, default=str), "")
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

        return conversation

    def list_interviews(self, top):
        """fetch a list of interviews"""

        query = """
            SELECT
                i.id,
                i.created,
                i.user_id,
                i.topic_id,
                i.status,
                i.data,
                i.completed,
                i.summary,
                t.name AS topic_name,
                t.description AS topic_description,
                t.areas AS topic_areas,
                s.name AS scope_name,
                i.approved_by_user_id,
                i.approved_on,
                i.voice_mode,
                i.voice_session_metadata
            FROM interview i
            JOIN topic t ON i.topic_id = t.id
            JOIN scope s ON t.scope_id = s.id
            ORDER BY created DESC
            LIMIT %s
        """
        logging.info(f"query: {query}")
        values = (top,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            r = InterviewRecord(
                id=record[0],
                created=record[1],
                user_id=record[2],
                topic_id=record[3],
                status=record[4],
                data=record[5],
                completed=record[6],
                summary=record[7],
                topic_name=record[8],
                topic_description=record[9],
                topic_areas=record[10],
                scope_name=record[11],
                approved_by_user_id=record[12],
                approved_on=record[13],
                voice_mode=record[14],
                voice_session_metadata=record[15],
            )
            results.append(r.to_interview())
        return results

    def list_interviews_by_user(self, user_id, top):
        """fetch a list of interviews by user"""

        query = """
            SELECT data FROM interview
            WHERE user_id = %s
            ORDER BY created DESC
            LIMIT %s
        """
        logging.info(f"query: {query}")
        values = (user_id, top,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            results.append(record[0])
        return results

    def update(self, conversation):
        """updates a conversation object"""

        query = """
            UPDATE conversation
            SET data = %s
            WHERE id = %s
        """
        values = (json.dumps(conversation, default=str),
                  conversation["conversationId"])
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def get(self, conversation_id):
        """fetch a conversation by id"""

        query = """
            SELECT data
            FROM conversation
            WHERE id = %s
        """
        logging.info(f"query: {query}")
        values = (conversation_id,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        return record[0] if record else None

    def list(self, top):
        """fetch a list of conversations"""

        query = """
            SELECT data FROM conversation
            ORDER BY created DESC
            LIMIT %s
        """
        logging.info(f"query: {query}")
        values = (top,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            results.append(record[0])
        return results

    def list_by_user(self, user_id, top):
        """fetch a list of conversations by user"""

        query = """
            SELECT data FROM conversation
            WHERE user_id = %s
            ORDER BY created DESC
            LIMIT %s
        """
        logging.info(f"query: {query}")
        values = (user_id, top,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            results.append(record[0])
        return results

    def get_topic_by_name(self, name):
        """get topic by name"""
        query = """
            SELECT id, name, description, areas, scope_id
            FROM topic
            WHERE name = %s
        """
        logging.info(f"query: {query}")
        values = (name,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if record:
            return {
                "id": record[0],
                "name": record[1],
                "description": record[2],
                "areas": record[3],
                "scope_id": record[4]
            }
        else:
            return None

    def get_topic_by_id(self, id):
        """get topic by id"""
        query = """
            SELECT id, name, description, areas, scope_id
            FROM topic
            WHERE id = %s
        """
        logging.info(f"query: {query}")
        values = (id,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if record:
            return {
                "id": record[0],
                "name": record[1],
                "description": record[2],
                "areas": record[3],
                "scope_id": record[4]
            }
        else:
            return None

    def create_scope(self, name, description, created):
        """creates a new scope"""
        id = str(uuid.uuid4())

        query = """
            INSERT INTO scope (id, created, name, description)
            VALUES (%s, %s, %s, %s)
        """
        values = (id, created, name, description)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

        return {
            "id": id,
            "name": name,
            "description": description,
            "created": created
        }

    def update_scope(self, id, name, description):
        """updates a scope"""

        query = """
            UPDATE scope
            SET name = %s, description = %s
            WHERE id = %s
        """
        values = (name, description, id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def get_scope(self, scope_id):
        """get scope by id"""
        query = """
            SELECT id, name, description, created
            FROM scope
            WHERE id = %s
        """
        logging.info(f"query: {query}")
        values = (scope_id,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if record:
            return {
                "id": record[0],
                "name": record[1],
                "description": record[2],
                "created": record[3]
            }
        else:
            return None

    def delete_scope(self, scope_id):
        """delete scope by id"""

        query = """
            DELETE FROM scope
            WHERE id = %s
        """
        logging.info(f"query: {query}")
        values = (scope_id,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            conn.execute(query, values)

    def list_scopes(self, top=50):
        """fetch a list of scopes"""

        query = """
            SELECT id, name, description, created
            FROM scope
            ORDER BY created DESC
            LIMIT %s
        """
        logging.info(f"query: {query}")
        values = (top,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            results.append({
                "id": record[0],
                "name": record[1],
                "description": record[2],
                "created": record[3]
            })
        return results

    def create_topic(self, name, description, areas, scope_id, created):
        """creates a new topic"""
        id = str(uuid.uuid4())

        query = """
            INSERT INTO topic (id, created, scope_id, name, description, areas)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (id, created, scope_id, name, description, json.dumps(areas))
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

        return {
            "id": id,
            "name": name,
            "description": description,
            "areas": areas,
            "scope_id": scope_id,
            "created": created
        }

    def list_topics_by_scope(self, scope_id):
        """list topics by scope id"""
        query = """
            SELECT id, name, description, areas, created
            FROM topic
            WHERE scope_id = %s
            ORDER BY created DESC
        """
        logging.info(f"query: {query}")
        values = (scope_id,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            results.append({
                "id": record[0],
                "name": record[1],
                "description": record[2],
                "areas": record[3],
                "created": record[4]
            })
        return results

    def list_approved_interviews_by_topic(self, topic_id):
        """list approved interviews by topic id"""
        query = """
            SELECT i.id, i.created, i.topic_id, i.user_id, i.status,
                   i.data, i.completed, i.summary, t.name as topic_name,
                   t.description as topic_description, t.areas as topic_areas,
                   s.name as scope_name, i.voice_mode, i.voice_session_metadata
            FROM interview i
            JOIN topic t ON i.topic_id = t.id
            JOIN scope s ON t.scope_id = s.id
            WHERE i.topic_id = %s AND i.status = %s
            ORDER BY i.completed DESC
        """
        logging.info(f"query: {query}")
        values = (topic_id, InterviewStatus.APPROVED.value)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            interview_record = InterviewRecord(
                id=record[0],
                created=record[1],
                topic_id=record[2],
                user_id=record[3],
                status=record[4],
                data=record[5],
                completed=record[6],
                summary=record[7],
                topic_name=record[8],
                topic_description=record[9],
                topic_areas=record[10],
                scope_name=record[11],
                voice_mode=record[12],
                voice_session_metadata=record[13],
            )
            results.append(interview_record.to_interview())
        return results

    def update_conversation_summary(self, conversation_id, summary):
        """updates a conversation summary"""

        query = """
            UPDATE conversation
            SET summary = %s
            WHERE id = %s
        """
        values = (summary, conversation_id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def update_topic(self, id, name, description, areas):
        """updates a topic"""

        query = """
            UPDATE topic
            SET name = %s, description = %s, areas = %s
            WHERE id = %s
        """
        values = (name, description, json.dumps(areas), id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def delete_topic(self, topic_id):
        """delete topic by id"""

        query = """
            DELETE FROM topic
            WHERE id = %s
        """
        logging.info(f"query: {query}")
        values = (topic_id,)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            conn.execute(query, values)

    def get_available_interviews(self, user_id):
        """
        Returns interviews with a status of notstarted and started
        Joins with topic and scope tables to return additional information
        Returns: scope_name, topic_name, topic_description, status, interview_id, status
        """

        query = """
            SELECT
                s.name AS scope_name,
                t.name AS topic_name,
                t.description AS topic_description,
                i.status,
                i.id AS interview_id
            FROM interview i
            JOIN topic t ON i.topic_id = t.id
            JOIN scope s ON t.scope_id = s.id
            WHERE i.user_id = %s AND i.status in (%s,%s)
            ORDER BY i.created DESC
        """
        logging.info(f"query: {query}")
        values = (user_id, InterviewStatus.NOT_STARTED.value,
                  InterviewStatus.STARTED.value)
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            r = InterviewRecord(
                id=record[4],
                user_id=user_id,
                status=record[3],
                topic_name=record[1],
                topic_description=record[2],
                scope_name=record[0],
            )
            results.append(r.to_interview())
        return results

    def get_inflight_interviews(self, topic_id):
        """
        Returns interviews for a topic in any status other than approved/rejected
        Joins with topic and scope tables to return additional information
        Returns: scope_name, topic_name, topic_description, status, interview_id, user_id, created
        """

        query = """
            SELECT
                s.name AS scope_name,
                t.name AS topic_name,
                t.description AS topic_description,
                i.status,
                i.id AS interview_id,
                i.user_id,
                i.created
            FROM interview i
            JOIN topic t ON i.topic_id = t.id
            JOIN scope s ON t.scope_id = s.id
            WHERE i.topic_id = %s
            AND i.status not in (%s,%s)
            ORDER BY i.created DESC
        """
        logging.info(f"query: {query}")
        values = (
            topic_id,
            InterviewStatus.APPROVED.value,
            InterviewStatus.REJECTED.value,
        )
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            r = InterviewRecord(
                id=record[4],
                status=record[3],
                topic_name=record[1],
                topic_description=record[2],
                scope_name=record[0],
                user_id=record[5],
                created=record[6],
            )
            results.append(r.to_interview())
        return results

    def update_interview(self, interview):
        """updates an interview object"""

        query = """
            UPDATE interview
            SET
                status = %s,
                data = %s,
                summary=%s,
                approved_by_user_id = %s,
                approved_on = %s,
                voice_mode = %s,
                voice_session_metadata = %s
            WHERE id = %s
        """
        record = interview.to_record()
        values = (record.status, record.data, record.summary,
                  record.approved_by_user_id, record.approved_on, record.voice_mode, record.voice_session_metadata, record.id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def update_interview_transcription(self, interview_id, transcription_data):
        """Updates interview transcription data for voice interviews"""

        query = """
            UPDATE interview
            SET data = %s
            WHERE id = %s
        """
        values = (json.dumps(transcription_data, default=str), interview_id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def append_voice_transcription_entry(self, interview_id, question, answer):
        """Appends a new transcription entry to existing interview data"""

        query = """
            UPDATE interview
            SET data = COALESCE(data, '[]'::jsonb) || %s::jsonb
            WHERE id = %s
        """
        new_entry = json.dumps([{"q": question, "a": answer}])
        values = (new_entry, interview_id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def get_voice_conversation_history(self, interview_id, max_characters=40960):
        """Gets formatted conversation history for voice sessions with character limit"""

        query = """
            SELECT data
            FROM interview
            WHERE id = %s
        """
        values = (interview_id,)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if not record or not record[0]:
            return []

        conversation_data = record[0]
        if not isinstance(conversation_data, list):
            return []

        # Format and truncate conversation history for Nova Sonic
        total_characters = 0
        formatted_history = []

        # Process from most recent backwards to stay within character limit
        for i in range(len(conversation_data) - 1, -1, -1):
            entry = conversation_data[i]
            question = entry.get('q', '')
            answer = entry.get('a', '')

            # Truncate individual messages to 1024 characters as per requirements
            truncated_question = question[:1024] if len(
                question) > 1024 else question
            truncated_answer = answer[:1024] if len(answer) > 1024 else answer

            entry_length = len(truncated_question) + len(truncated_answer)

            if total_characters + entry_length > max_characters:
                break

            formatted_history.insert(0, {
                'q': truncated_question,
                'a': truncated_answer
            })

            total_characters += entry_length

        return formatted_history

    def update_voice_session_metadata(self, interview_id, metadata):
        """Updates voice session metadata for an interview"""

        query = """
            UPDATE interview
            SET voice_session_metadata = %s
            WHERE id = %s
        """
        values = (json.dumps(metadata, default=str), interview_id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def update_voice_session_status(self, interview_id, session_id, status):
        """Updates voice session status for a specific session"""

        query = """
            UPDATE interview
            SET voice_session_metadata = jsonb_set(
                COALESCE(voice_session_metadata, '{}'::jsonb),
                %s,
                %s::jsonb
            )
            WHERE id = %s
        """
        path = f'{{{session_id},status}}'
        status_data = json.dumps(status)
        values = (path, status_data, interview_id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def initialize_voice_session(self, interview_id, session_id, metadata):
        """Initializes voice session metadata for an interview"""

        query = """
            UPDATE interview
            SET voice_session_metadata = COALESCE(voice_session_metadata, '{}'::jsonb) || %s::jsonb
            WHERE id = %s
        """
        session_data = {
            session_id: {
                **metadata,
                'createdAt': datetime.now(timezone.utc).isoformat()
            }
        }
        values = (json.dumps(session_data, default=str), interview_id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def get_voice_session_metadata(self, interview_id, session_id=None):
        """Gets voice session metadata for an interview"""

        query = """
            SELECT voice_session_metadata
            FROM interview
            WHERE id = %s
        """
        values = (interview_id,)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if not record:
            return None

        metadata = record[0] or {}

        if session_id:
            return metadata.get(session_id)

        return metadata

    def enable_voice_mode(self, interview_id):
        """Enables voice mode for an interview"""

        query = """
            UPDATE interview
            SET voice_mode = true
            WHERE id = %s
        """
        values = (interview_id,)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def get_interview_voice_info(self, interview_id):
        """Gets basic interview info for voice session validation"""

        query = """
            SELECT id, user_id, topic_id, status, voice_mode
            FROM interview
            WHERE id = %s
        """
        values = (interview_id,)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if not record:
            return None

        return {
            'id': record[0],
            'user_id': record[1],
            'topic_id': record[2],
            'status': record[3],
            'voice_mode': record[4] or False
        }

    def get_interview(self, id) -> Interview:
        """fetch an interview by id with all fields and topic information"""

        query = """
            SELECT
                i.id,
                i.created,
                i.user_id,
                i.topic_id,
                i.status,
                i.data,
                i.completed,
                i.summary,
                t.name AS topic_name,
                t.description AS topic_description,
                t.areas AS topic_areas,
                s.name AS scope_name,
                i.approved_by_user_id,
                i.approved_on,
                i.voice_mode,
                i.voice_session_metadata
            FROM interview i
            JOIN topic t ON i.topic_id = t.id
            JOIN scope s ON t.scope_id = s.id
            WHERE i.id = %s
        """
        values = (id,)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if record:
            record = InterviewRecord(
                id=record[0],
                created=record[1],
                user_id=record[2],
                topic_id=record[3],
                status=record[4],
                data=record[5],
                completed=record[6],
                summary=record[7],
                topic_name=record[8],
                topic_description=record[9],
                topic_areas=record[10],
                scope_name=record[11],
                approved_by_user_id=record[12],
                approved_on=record[13],
                voice_mode=record[14],
                voice_session_metadata=record[15],
            )
            return record.to_interview()
        else:
            return None

    def get_latest_approved_interview(self, topic_id) -> Interview:
        """fetch the latest approved interview by topic"""

        query = """
            SELECT
                id,
                created,
                user_id,
                topic_id,
                status,
                data,
                completed,
                summary,
                approved_by_user_id,
                approved_on,
                voice_mode,
                voice_session_metadata
            FROM interview
            WHERE topic_id = %s
            AND status = %s
            ORDER BY completed DESC
            LIMIT 1
        """
        values = (topic_id, InterviewStatus.APPROVED.value)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if record:
            record = InterviewRecord(
                id=record[0],
                created=record[1],
                user_id=record[2],
                topic_id=record[3],
                status=record[4],
                data=record[5],
                completed=record[6],
                summary=record[7],
                approved_by_user_id=record[8],
                approved_on=record[9],
                voice_mode=record[10],
                voice_session_metadata=record[11],
            )
            return record.to_interview()
        else:
            return None

    def get_inflight_interview_by_user_topic(self, user_id, topic_id) -> Interview:
        """returns an in-flight interview by user and topic"""

        query = """
            SELECT
                i.id,
                i.created,
                i.user_id,
                i.topic_id,
                i.status,
                i.data,
                i.completed,
                i.summary,
                i.approved_by_user_id,
                i.approved_on,
                i.voice_mode,
                i.voice_session_metadata
            FROM interview i
            WHERE i.user_id = %s AND i.topic_id = %s
            AND i.status not in (%s,%s)
        """
        values = (
            user_id,
            topic_id,
            InterviewStatus.APPROVED.value,
            InterviewStatus.REJECTED.value,
        )

        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        if record:
            record = InterviewRecord(
                id=record[0],
                created=record[1],
                user_id=record[2],
                topic_id=record[3],
                status=record[4],
                data=record[5],
                completed=record[6],
                summary=record[7],
                approved_by_user_id=record[8],
                approved_on=record[9],
                voice_mode=record[10],
                voice_session_metadata=record[11],
            )
            return record.to_interview()
        else:
            return None

    def create_interview(self, interview: Interview):
        """creates a new interview"""

        logging.info(f"db.create_interview()")

        query = """
            INSERT INTO interview (id, created, topic_id, user_id, status, data, summary, completed, voice_mode, voice_session_metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        record = interview.to_record()
        values = (record.id, record.created, record.topic_id, record.user_id,
                  record.status, record.data, record.summary, record.completed, record.voice_mode, record.voice_session_metadata)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

        return interview

    def get_assigned_user(self, topic_id):
        """get user assigned to a topic"""

        query = """
            SELECT user_id
            FROM interview
            WHERE topic_id = %s
        """
        values = (topic_id,)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")
        with self.connect() as conn:
            record = conn.execute(query, values).fetchone()

        return record[0] if record else None

    def get_available_reviews(self, user_id):
        """
        Returns interviews that are in a status to be reviewed
        and not for the same user.
        """

        query = """
            SELECT
                s.name AS scope_name,
                t.name AS topic_name,
                t.description AS topic_description,
                i.status,
                i.id AS interview_id,
                i.completed,
                i.user_id
            FROM interview i
            JOIN topic t ON i.topic_id = t.id
            JOIN scope s ON t.scope_id = s.id
            WHERE i.status IN (%s, %s, %s)
            AND i.user_id != %s
            ORDER BY i.created DESC
        """
        values = (
            InterviewStatus.PROCESSING.value,
            InterviewStatus.PENDING_REVIEW.value,
            InterviewStatus.REVIEWING.value,
            user_id,
        )
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")
        with self.connect() as conn:
            records = conn.execute(query, values).fetchall()

        results = []
        for record in records:
            r = InterviewRecord(
                id=record[4],
                status=record[3],
                topic_name=record[1],
                topic_description=record[2],
                scope_name=record[0],
                completed=record[5],
                user_id=record[6]
            )
            results.append(r.to_interview())
        return results

    def end_interview(self, interview: Interview):
        """ends an interview object"""

        query = """
            UPDATE interview
            SET
                status = %s,
                completed = %s
            WHERE id = %s
        """
        record = interview.to_record()
        values = (
            record.status,
            record.completed,
            record.id,
        )
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def summarize_interview(self, interview: Interview):
        """updates an interview's summary and status"""

        query = """
            UPDATE interview
            SET
                status = %s,
                summary = %s
            WHERE id = %s
        """
        record = interview.to_record()
        values = (
            record.status,
            record.summary,
            record.id,
        )
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

    def get_setting(self, key: str) -> str:
        """Retrieve a setting value by key"""
        try:
            query = "SELECT value FROM settings WHERE key = %s"
            logging.info(f"query: {query}")
            values = (key,)
            logging.info(f"values: {values}")

            with self.connect() as conn:
                record = conn.execute(query, values).fetchone()

            return record[0] if record else None
        except Exception as e:
            logging.error(f"Error retrieving setting '{key}': {e}")
            raise

    def set_setting(self, key: str, value: str) -> None:
        """Set or update a setting value"""
        try:
            query = """
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """
            logging.info(f"query: {query}")
            values = (key, value)
            logging.info(f"values: {values}")

            with self.connect() as conn:
                conn.execute(query, values)
        except Exception as e:
            logging.error(f"Error setting '{key}' to '{value}': {e}")
            raise

    def get_talk_mode_enabled(self) -> bool:
        """Get talk mode enabled status with default fallback to True"""
        try:
            value = self.get_setting('talk_mode_enabled')
            if value is None:
                # Setting doesn't exist, return default True
                return True
            # Convert string value to boolean
            return value.lower() == 'true'
        except Exception as e:
            logging.error(f"Error retrieving talk mode setting: {e}")
            # Return default True on any error for backward compatibility
            return True
