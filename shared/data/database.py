import os
import uuid
import logging
import json
import time
import threading
import psycopg
import boto3
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
                i.summary
            FROM interview
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

    def update_interview(self, interview):
        """updates an interview object"""

        query = """
            UPDATE interview
            SET
                status = %s,
                data = %s,
                summary=%s
            WHERE id = %s
        """
        record = interview.to_record()
        values = (record.status, record.data, record.summary, record.id)
        logging.info(f"query: {query}")
        logging.info(f"values: {values}")

        with self.connect() as conn:
            conn.execute(query, values)

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
                s.name AS scope_name
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
            )
            return record.to_interview()
        else:
            return None

    def get_interview_by_user_topic(self, user_id, topic_id) -> Interview:
        """returns an interview by user and topic"""

        query = """
            SELECT
                i.id,
                i.created,
                i.user_id,
                i.topic_id,
                i.status,
                i.data,
                i.completed,
                i.summary
            FROM interview i
            WHERE i.user_id = %s AND i.topic_id = %s
        """
        values = (user_id, topic_id,)
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
            )
            return record.to_interview()
        else:
            return None

    def create_interview(self, interview: Interview):
        """creates a new interview"""

        logging.info(f"db.create_interview()")

        query = """
            INSERT INTO interview (id, created, topic_id, user_id, status, data, summary, completed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        record = interview.to_record()
        values = (record.id, record.created, record.topic_id, record.user_id,
                  record.status, record.data, record.summary, record.completed)
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

    def get_available_reviews(self):
        """
        Returns interviews that are in a status to be reviewed.
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
            WHERE i.status IN (%s, %s, %s, %s, %s, %s)
            ORDER BY i.created DESC
        """
        values = (
            InterviewStatus.PROCESSING.value,
            InterviewStatus.PENDING_REVIEW.value,
            InterviewStatus.REVIEWING.value,
            InterviewStatus.PENDING_APPROVAL.value,
            InterviewStatus.APPROVED.value,
            InterviewStatus.REJECTED.value,
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
