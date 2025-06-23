import logging
import json
import sys
from shared.config import config


class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs as JSON"""

    def format(self, record):
        log_record = {
            "lvl": record.levelname,
            "msg": record.getMessage()
        }
        return json.dumps(log_record)


# Configure root logger with JSON output to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())

# Configure logging with basicConfig using log level from config
logging.basicConfig(level=config.log_level, force=True)

# Remove any existing handlers from root logger
root = logging.getLogger()
for h in root.handlers:
    root.removeHandler(h)

# Add our JSON handler
root.addHandler(handler)

# Create a logger instance for the application
log = root

# Disable werkzeug http request logging to avoid logging health checks
# but keep errors visible
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.ERROR)


def debug(obj):
    """log object as json if in debug mode"""
    if logging.getLogger().level <= logging.DEBUG:
        logging.debug(json.dumps(obj, indent=2, default=str))


def info(obj):
    """log object as json if in info mode or debug mode"""
    if logging.getLogger().level <= logging.INFO:
        logging.info(json.dumps(obj, indent=2, default=str))


def llm(input, output):
    """log llm calls to stdout using specific format"""
    payload = {
        "input": input,
        "output": output
    }
    print(f"LLM: {json.dumps(payload, default=str)}")
