import os
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Optionally, set up file-based logging
# log_path = os.path.join(os.getcwd(), 'logs')
# os.makedirs(log_path, exist_ok=True)
# log_file = os.path.join(log_path, 'app.log')

logger = structlog.get_logger()
fastapi_logger = logger.bind(component='fastapi_app')
celery_logger = logger.bind(component='celery')

# # Example configuration for logging to a file
# structlog.configure_once(
#     processors=[
#         structlog.stdlib.add_log_level,
#         structlog.stdlib.PositionalArgumentsFormatter(),
#         structlog.processors.TimeStamper(fmt="iso"),
#         structlog.processors.JSONRenderer(),
#         structlog.processors.StackInfoRenderer(),
#         structlog.processors.format_exc_info,
#     ],
#     context_class=dict,
#     logger_factory=structlog.stdlib.LoggerFactory(),
# )
