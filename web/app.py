from http.client import HTTPException
import logging
from flask import Flask, request, render_template, jsonify, redirect, g, current_app, url_for, session
import markdown2
from markupsafe import Markup

from auth import get_current_user, is_admin, configure_auth, login_required
from shared.data import database

# otel
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

# Import route modules
import chatbot
import interviews
import reviews
import admin
import api
import kb
import docs


def create_app():
    """Create and configure the Flask application"""

    app = Flask(__name__)

    # Configure authentication
    configure_auth(app)

    # Setup OpenTelemetry
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    FlaskInstrumentor().instrument_app(app)
    BotocoreInstrumentor().instrument()

    # initialize database client
    db = database.Database()

    @app.template_filter('markdown')
    def render_markdown(text):
        """Render Markdown text to HTML"""
        if text is None:
            return ""

        # Use markdown2 with extras for better rendering
        html = markdown2.markdown(text, extras=[
            "fenced-code-blocks",
            "tables",
            "break-on-newline",
            "header-ids",
            "smarty-pants",
            "cuddled-lists"
        ])

        return Markup(html)

    @app.before_request
    def before_request():
        """log http request (except for health checks)"""
        if request.path != "/health":
            logging.info(f"HTTP {request.method} {request.url}")

    @app.after_request
    def after_request(response):
        """log http response (except for health checks)"""
        if request.path != "/health":
            logging.info(
                f"HTTP {request.method} {request.url} {response.status_code}")
        return response

    @app.context_processor
    def inject_user():
        """
        Context processor to get current user and store it in g
        Makes user information available to all templates
        """
        try:
            if not hasattr(g, 'current_user'):
                g.current_user = get_current_user()

            return {
                'current_user': g.current_user,
                'is_authenticated': g.current_user is not None
            }
        except Exception as e:
            current_app.logger.error(f"Error injecting user context: {str(e)}")
            return {
                'current_user': None,
                'is_authenticated': False
            }

    @app.context_processor
    def inject_admin_status():
        """
        Context processor to store and provide admin status
        Makes is_admin available to all templates
        """
        try:
            if not hasattr(g, 'is_admin'):
                g.is_admin = is_admin()  # Using the is_admin function from auth.py

            return {
                'is_admin': g.is_admin
            }
        except Exception as e:
            current_app.logger.error(f"Error injecting admin status: {str(e)}")
            return {
                'is_admin': False
            }

    @app.route("/health")
    def health_check():
        return "healthy"

    @app.route("/")
    @app.route("/index")
    def index():
        """home page"""
        return render_template("index.html")

    # Error handlers
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'message': 'Unauthorized access'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'message': 'Forbidden'}), 403

    @app.errorhandler(Exception)
    def handle_error(error):
        code = 500
        if isinstance(error, HTTPException):
            code = error.code
        return jsonify({
            'error': str(error),
            'status_code': code
        }), code

    # Register routes from modules
    chatbot.register_routes(app, db)
    interviews.register_routes(app, db)
    reviews.register_routes(app, db)
    admin.register_routes(app, db)
    api.register_routes(app, db)
    kb.register_routes(app, db)
    docs.register_routes(app, db)

    return app
