import uuid
from datetime import datetime, timezone
from enum import Enum
import json
import logging


class InterviewStatus(Enum):
    """Enum for interview status values"""
    NOT_STARTED = "notstarted"
    STARTED = "started"
    PROCESSING = "processing"
    PENDING_REVIEW = "pendingreview"
    REVIEWING = "reviewing"
    PENDING_APPROVAL = "pendingapproval"
    APPROVED = "approved"
    REJECTED = "rejected"


class Question:
    """Question domain object"""

    def __init__(self, question, answer=None):
        self.question = question
        self.answer = answer


class InterviewRecord:
    """Database record representation"""

    def __init__(
        self,
        id,
        user_id=None,
        topic_id=None,
        status=None,
        data=None,
        summary=None,
        created=None,
        completed=None,
        topic_name=None,
        topic_description=None,
        topic_areas=None,
        scope_name=None,
        approved_by_user_id=None,
        approved_on=None,
        voice_mode=None,
        voice_session_metadata=None,
    ):
        """
        Initialize an InterviewRecord object that maps to the interview database table.

        CREATE TABLE IF NOT EXISTS interview (
            id UUID PRIMARY KEY,
            created TIMESTAMP WITH TIME ZONE NOT NULL,
            topic_id UUID REFERENCES topic(id),
            user_id VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            data JSONB NOT NULL, -- [{"question":"", "answer":""}]
            completed TIMESTAMP WITH TIME ZONE NOT NULL,
            summary VARCHAR NOT NULL,
            voice_mode BOOLEAN DEFAULT FALSE,
            voice_session_metadata JSONB DEFAULT '{}'::jsonb
        );
        """
        logging.info(f"creating interview record: {id}")

        self.id = id
        self.created = created
        self.topic_id = topic_id
        self.user_id = user_id
        self.status = status
        self.data = data
        self.completed = completed
        self.summary = summary
        self.topic_name = topic_name
        self.topic_description = topic_description
        self.topic_areas = topic_areas
        self.scope_name = scope_name
        self.approved_by_user_id = approved_by_user_id
        self.approved_on = approved_on
        self.voice_mode = voice_mode
        self.voice_session_metadata = voice_session_metadata

    def to_interview(self) -> 'Interview':
        """Convert database record to domain object"""
        logging.info(
            f"converting interview record to domain object: {self.id}")

        result = Interview(
            id=self.id,
            created=self.created,
            topic_id=self.topic_id,
            user_id=self.user_id,
            completed=self.completed,
            summary=self.summary,
            topic_name=self.topic_name,
            topic_description=self.topic_description,
            scope_name=self.scope_name,
            topic_areas=self.topic_areas,
            approved_by_user_id=self.approved_by_user_id,
            approved_on=self.approved_on,
            voice_mode=self.voice_mode,
            voice_session_metadata=self.voice_session_metadata,
        )

        # convert status string to enum
        result.status = InterviewStatus(self.status)

        # psycopg should return a list of dicts
        # convert list of dicts into list of Question objects
        result.questions = []
        if self.data:
            for q in self.data:
                question = Question(
                    question=q["q"],
                    answer=q.get("a", ""),
                )
                result.questions.append(question)

        # handle voice_session_metadata deserialization
        if isinstance(self.voice_session_metadata, str):
            try:
                result.voice_session_metadata = json.loads(
                    self.voice_session_metadata)
            except (json.JSONDecodeError, TypeError):
                result.voice_session_metadata = {}
        elif self.voice_session_metadata is None:
            result.voice_session_metadata = {}
        else:
            result.voice_session_metadata = self.voice_session_metadata

        return result


class Interview():
    """Interview domain representation"""

    def __init__(
        self,
        id,
        created=None,
        topic_id=None,
        user_id=None,
        status=None,
        completed=None,
        summary=None,
        topic_name=None,
        topic_description=None,
        topic_areas=None,
        scope_name=None,
        user_name=None,
        approved_by_user_id=None,
        approved_on=None,
        voice_mode=None,
        voice_session_metadata=None,
    ):
        logging.info(f"creating interview domain object: {id}")

        self.id = id
        self.created = created
        self.user_id = user_id
        self.topic_id = topic_id
        self.status = status
        self.completed = completed
        self.summary = summary
        self.topic_name = topic_name
        self.topic_description = topic_description
        self.topic_areas = topic_areas
        self.scope_name = scope_name
        self.questions = []
        self.user_name = user_name
        self.approved_by_user_id = approved_by_user_id
        self.approved_on = approved_on
        self.voice_mode = voice_mode if voice_mode is not None else False
        self.voice_session_metadata = voice_session_metadata if voice_session_metadata is not None else {}

    @staticmethod
    def new(topic_id, user_id):
        """Create and return a new Interview object with default values"""
        return Interview(
            id=str(uuid.uuid4()),
            status=InterviewStatus.NOT_STARTED,
            created=datetime.now(timezone.utc),
            topic_id=topic_id,
            user_id=user_id,
        )

    def add_question(self, question):
        """Add a question to the interview"""
        self.questions.append(Question(question=question))

    def to_record(self) -> InterviewRecord:
        """Convert an Interview to an InterviewRecord"""

        logging.info(f"converting interview to record: {self.id}")
        result = InterviewRecord(
            id=self.id,
            created=self.created,
            topic_id=self.topic_id,
            user_id=self.user_id,
            completed=self.completed,
            summary=self.summary,
            topic_name=self.topic_name,
            topic_description=self.topic_description,
            scope_name=self.scope_name,
            topic_areas=self.topic_areas,
            approved_by_user_id=self.approved_by_user_id,
            approved_on=self.approved_on,
            voice_mode=self.voice_mode,
            voice_session_metadata=self.voice_session_metadata,
        )

        # serialize the enum to a string
        result.status = self.status.value

        # convert list of Question objects into list of dicts
        data = []
        for question in self.questions:
            q = {"q": question.question}
            if question.answer:
                q["a"] = question.answer
            data.append(q)
        result.data = json.dumps(data, default=str)

        # serialize voice_session_metadata to JSON string
        result.voice_session_metadata = json.dumps(
            self.voice_session_metadata, default=str)

        return result


class User:
    """User domain object"""

    def __init__(self, id, username, email, status, enabled, created_at, last_modified):
        self.id = id
        self.username = username
        self.email = email
        self.status = status
        self.enabled = enabled
        self.created_at = created_at
        self.last_modified = last_modified
