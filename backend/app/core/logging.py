"""Structured JSON logging (OWASP A09). See docs/LOGGING_AND_AUDIT.md."""
import logging

import structlog


def configure_logging(debug: bool) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,   # request_id etc.
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()
