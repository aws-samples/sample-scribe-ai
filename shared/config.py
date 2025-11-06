import os
import logging
from typing import Optional


class EnvironmentVariableNotSetError(Exception):
    """Exception raised when a required environment variable is not set."""
    pass


class Config:
    def __init__(self):
        self._port = os.getenv("PORT", "8080")
        level = os.getenv("LOG_LEVEL", "INFO")
        self._log_level = getattr(logging, level, logging.INFO)
        self._region = os.getenv("AWS_REGION")
        self._cognito_domain = os.getenv("AWS_COGNITO_DOMAIN")
        self._cognito_pool_id = os.getenv("AWS_COGNITO_USER_POOL_ID")
        self._client_id = os.getenv("AWS_COGNITO_APP_CLIENT_ID")
        self._client_secret = os.getenv("AWS_COGNITO_APP_CLIENT_SECRET")
        self._redirect_uri = os.getenv("AWS_COGNITO_REDIRECT_URL")
        self._scribe_summary_id = os.getenv("SCRIBE_SUMMARY_ID")
        self._document_generator_id = os.getenv("DOCUMENT_GENERATOR_ID")
        self._knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")
        self._data_source_id = os.getenv("DATA_SOURCE_ID")
        self._kb_generator_id = os.getenv("KB_GENERATOR_ID")
        self._prompt_interview_user = os.getenv("PROMPT_INTERVIEW_USER")
        self._prompt_interview_system = os.getenv("PROMPT_INTERVIEW_SYSTEM")
        self._prompt_interview_voice = os.getenv("PROMPT_INTERVIEW_VOICE")
        self._prompt_chat_system = os.getenv("PROMPT_CHAT_SYSTEM")
        self._prompt_chat_user = os.getenv("PROMPT_CHAT_USER")
        self._prompt_chat_reword = os.getenv("PROMPT_CHAT_REWORD")
        self._flask_secret_key_name = os.getenv("FLASK_SECRET_KEY_NAME")
        self._s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        self._postgres_host = os.getenv("POSTGRES_HOST")
        self._postgres_dbname = os.getenv("POSTGRES_DB")
        self._postgres_user = os.getenv("POSTGRES_USER")
        self._postgres_password = os.getenv("POSTGRES_PASSWORD")
        self._postgres_secret_arn = os.getenv("DB_SECRET_ARN")
        self._sqs_queue_url = os.getenv("SQS_QUEUE_URL")
        self._voice_lambda_function_name = os.getenv(
            "VOICE_LAMBDA_FUNCTION_NAME")
        self._appsync_events_endpoint = os.getenv("APPSYNC_EVENTS_ENDPOINT")

    def _get_env_var(self, name: str, value: Optional[str]) -> str:
        """Helper method to get environment variable value with validation."""
        if value is None:
            raise EnvironmentVariableNotSetError(
                f"Required environment variable '{name}' is not set")
        return value

    @property
    def region(self) -> str:
        return self._get_env_var("AWS_REGION", self._region)

    @property
    def aws_region(self) -> str:
        return self._get_env_var("AWS_REGION", self._region)

    @property
    def log_level(self) -> int:
        return self._get_env_var("LOG_LEVEL", self._log_level)

    @property
    def port(self) -> str:
        return self._get_env_var("PORT", self._port)

    @property
    def cognito_domain(self) -> str:
        return self._get_env_var("AWS_COGNITO_DOMAIN", self._cognito_domain)

    @property
    def cognito_pool_id(self) -> str:
        return self._get_env_var("AWS_COGNITO_USER_POOL_ID", self._cognito_pool_id)

    @property
    def client_id(self) -> str:
        return self._get_env_var("AWS_COGNITO_APP_CLIENT_ID", self._client_id)

    @property
    def client_secret(self) -> str:
        return self._get_env_var("AWS_COGNITO_APP_CLIENT_SECRET", self._client_secret)

    @property
    def redirect_uri(self) -> str:
        return self._get_env_var("AWS_COGNITO_REDIRECT_URL", self._redirect_uri)

    @property
    def scribe_summary_id(self) -> str:
        return self._get_env_var("SCRIBE_SUMMARY_ID", self._scribe_summary_id)

    @property
    def document_generator_id(self) -> str:
        return self._get_env_var("DOCUMENT_GENERATOR_ID", self._document_generator_id)

    @property
    def knowledge_base_id(self) -> str:
        return self._get_env_var("KNOWLEDGE_BASE_ID", self._knowledge_base_id)

    @property
    def data_source_id(self) -> str:
        return self._get_env_var("DATA_SOURCE_ID", self._data_source_id)

    @property
    def kb_generator_id(self) -> str:
        return self._get_env_var("KB_GENERATOR_ID", self._kb_generator_id)

    @property
    def prompt_interview_user(self) -> str:
        return self._get_env_var("PROMPT_INTERVIEW_USER", self._prompt_interview_user)

    @property
    def prompt_interview_system(self) -> str:
        return self._get_env_var("PROMPT_INTERVIEW_SYSTEM", self._prompt_interview_system)

    @property
    def prompt_interview_voice(self) -> str:
        return self._get_env_var("PROMPT_INTERVIEW_VOICE", self._prompt_interview_voice)

    @property
    def prompt_chat_system(self) -> str:
        return self._get_env_var("PROMPT_CHAT_SYSTEM", self._prompt_chat_system)

    @property
    def prompt_chat_user(self) -> str:
        return self._get_env_var("PROMPT_CHAT_USER", self._prompt_chat_user)

    @property
    def prompt_chat_reword(self) -> str:
        return self._get_env_var("PROMPT_CHAT_REWORD", self._prompt_chat_reword)

    @property
    def flask_secret_key_name(self) -> str:
        return self._get_env_var("FLASK_SECRET_KEY_NAME", self._flask_secret_key_name)

    @property
    def s3_bucket_name(self) -> str:
        return self._get_env_var("S3_BUCKET_NAME", self._s3_bucket_name)

    @property
    def sqs_queue_url(self) -> str:
        return self._get_env_var("SQS_QUEUE_URL", self._sqs_queue_url)

    @property
    def voice_lambda_function_name(self) -> str:
        return self._get_env_var("VOICE_LAMBDA_FUNCTION_NAME", self._voice_lambda_function_name)

    @property
    def appsync_events_endpoint(self) -> str:
        return self._get_env_var("APPSYNC_EVENTS_ENDPOINT", self._appsync_events_endpoint)

    @property
    def postgres_secret_arn(self) -> str:
        return self._postgres_secret_arn

    # these db envvars are used for local dev and are optional

    @property
    def postgres_host(self) -> str:
        return self._postgres_host

    @property
    def postgres_dbname(self) -> str:
        return self._postgres_dbname

    @property
    def postgres_user(self) -> str:
        return self._postgres_user

    @property
    def postgres_password(self) -> str:
        return self._postgres_password


# Create a singleton instance
config = Config()
