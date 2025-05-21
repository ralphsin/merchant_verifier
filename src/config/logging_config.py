#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: src/config/logging_config.py

"""
Logging Configuration Module

This module provides utilities for setting up and configuring logging
for the merchant verification system. It ensures consistent log formatting,
appropriate log levels, and log file management.
"""

# Standard library imports
import os
import sys
import logging
import datetime
from logging import handlers
from typing import Optional, Dict, Any, Union

# Define constants
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = "logs"


def setup_logging(
    log_level: Union[int, str] = DEFAULT_LOG_LEVEL,
    log_dir: str = DEFAULT_LOG_DIR,
    log_file: Optional[str] = None,
    console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Set up and configure the logging system.

    Args:
        log_level: Logging level (e.g., logging.INFO, 'INFO', 'DEBUG')
        log_dir: Directory to store log files
        log_file: Specific log file name (uses default if None)
        console: Whether to log to console
        log_format: Format string for log messages
        date_format: Format string for dates in log messages
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Root logger configured with appropriate handlers
    """
    # Convert string log level to numeric if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), DEFAULT_LOG_LEVEL)

    # Create root logger and set level
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates during reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(log_format, date_format)

    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    # Add file handler if log_dir is specified
    if log_dir:
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Generate default log filename if not provided
        if not log_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"merchant_verifier_{timestamp}.log"

        # Create full log path
        log_path = os.path.join(log_dir, log_file)

        # Create rotating file handler
        file_handler = handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

    # Log initial message
    root_logger.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    if log_dir:
        root_logger.info(f"Log file: {os.path.join(log_dir, log_file)}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This function returns a logger with the given name, creating it if necessary.
    If the root logger has not been configured, it will be configured with default settings.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        Logger instance
    """
    # Ensure root logger has at least one handler
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        setup_logging()

    # Get logger for specified name
    return logging.getLogger(name)


def set_log_level(
    logger_name: Optional[str] = None, level: Union[int, str] = logging.INFO
) -> None:
    """
    Set log level for a specific logger.

    Args:
        logger_name: Logger name (None for root logger)
        level: New log level as string or integer
    """
    # Convert string log level to numeric if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), DEFAULT_LOG_LEVEL)

    # Get logger
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()

    # Set level
    logger.setLevel(level)

    # Also update handler levels
    for handler in logger.handlers:
        handler.setLevel(level)

    logger.debug(
        f"Log level for {logger_name or 'root'} set to {logging.getLevelName(level)}"
    )


def capture_exceptions(logger: Optional[logging.Logger] = None) -> None:
    """
    Configure global exception handler to log unhandled exceptions.

    Args:
        logger: Logger to use (uses root logger if None)
    """
    if logger is None:
        logger = logging.getLogger()

    def exception_handler(exc_type, exc_value, exc_traceback):
        """Custom exception handler to log unhandled exceptions."""
        # Don't log KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Log the exception
        logger.critical(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    # Set the custom exception handler
    sys.excepthook = exception_handler


class LoggerAdapter(logging.LoggerAdapter):
    """
    Extended logger adapter with additional context information.

    This adapter allows adding context information to log messages,
    such as merchant ID or operation type.
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        """
        Initialize the logger adapter.

        Args:
            logger: Base logger to adapt
            extra: Dictionary with extra contextual information
        """
        super().__init__(logger, extra or {})

    def process(self, msg, kwargs):
        """
        Process the log message by adding context info.

        Args:
            msg: Log message
            kwargs: Additional keyword arguments

        Returns:
            Tuple of (modified message, kwargs)
        """
        # Add context information to message if available
        context_items = []

        for key, value in self.extra.items():
            if value is not None:
                context_items.append(f"{key}={value}")

        if context_items:
            context_str = ", ".join(context_items)
            msg = f"[{context_str}] {msg}"

        return msg, kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get a logger with context information.

    Args:
        name: Logger name
        **context: Additional context key-value pairs

    Returns:
        LoggerAdapter instance with context
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)


def get_merchant_logger(
    name: str, merchant_id: Optional[str] = None, merchant_name: Optional[str] = None
) -> LoggerAdapter:
    """
    Get a logger specifically for merchant operations.

    Args:
        name: Logger name
        merchant_id: Merchant ID for context
        merchant_name: Merchant name for context

    Returns:
        LoggerAdapter instance with merchant context
    """
    context = {}
    if merchant_id:
        context["merchant_id"] = merchant_id
    if merchant_name:
        context["merchant"] = merchant_name

    return get_context_logger(name, **context)
