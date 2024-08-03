import logging
import os

import structlog

FILENAME = os.environ.get("LOGS_FILENAME", "app.log")

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

stream_handler = logging.StreamHandler()
file_handler = logging.FileHandler(FILENAME)


stream_handler.setFormatter(logging.Formatter('%(message)s'))
file_handler.setFormatter(logging.Formatter('%(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[stream_handler, file_handler]
)

fastapi_logger = structlog.get_logger()
celery_logger = structlog.get_logger()
fastapi_logger = fastapi_logger.bind(component='fastapi_app')
celery_logger = celery_logger.bind(component='celery')
