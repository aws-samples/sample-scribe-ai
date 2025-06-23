from app import create_app
import signal
import sys
import logging
from shared.log import log
from shared.config import config

# Use the custom logger
log.warning("Starting Scribe AI application")

app = create_app()


def signal_handler(signal, frame):
    """immediate exits"""
    logging.warning('SIGTERM received, exiting...')
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    port = config.port
    log.warning(f"listening on http://localhost:{port}")

    # Set Flask's logger to use our configuration
    flask_logger = logging.getLogger('flask.app')
    for handler in logging.root.handlers:
        flask_logger.addHandler(handler)

    # Run with debug=False to avoid duplicate log messages
    app.run(host="0.0.0.0", port=port, debug=False)
