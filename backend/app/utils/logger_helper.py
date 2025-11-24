"""
Logger Helper Utility
Provides enhanced logging utilities for the application with informative error messages
and step-by-step API execution logging.
"""
import logging
import sys
import traceback
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for any module/route with enhanced formatting.
    
    Args:
        name: Logger name (typically module or route name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create enhanced formatter with more context
        formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger


def setup_route_logging():
    """
    Setup logging specifically for route handlers with enhanced configuration.
    """
    # Configure root logger for all routes
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create enhanced formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("app").setLevel(logging.INFO)
    
    logging.info("🔧 Route logging system configured - all route logs will be visible in console")


def log_api_request(logger: logging.Logger, method: str, path: str, **kwargs):
    """
    Log an API request with context information.
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path
        **kwargs: Additional context to log (user, params, etc.)
    """
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.info(f"🚀 API Request: {method} {path}" + (f" | {context}" if context else ""))


def log_api_response(logger: logging.Logger, method: str, path: str, status_code: int = None, **kwargs):
    """
    Log an API response with status information.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: API endpoint path
        status_code: HTTP status code
        **kwargs: Additional context to log
    """
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    status_info = f" | Status: {status_code}" if status_code else ""
    logger.info(f"✅ API Response: {method} {path}{status_info}" + (f" | {context}" if context else ""))


def log_error(logger: logging.Logger, error: Exception, context: str = "", include_traceback: bool = True):
    """
    Log an error with full context and traceback.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context about where the error occurred
        include_traceback: Whether to include full traceback
    """
    error_msg = f"❌ Error: {type(error).__name__}: {str(error)}"
    if context:
        error_msg = f"{error_msg} | Context: {context}"
    
    logger.error(error_msg)
    
    if include_traceback:
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")


def log_step(logger: logging.Logger, step_description: str, **kwargs):
    """
    Log a step in API execution with optional context.
    
    Args:
        logger: Logger instance
        step_description: Description of the step being performed
        **kwargs: Additional context about the step
    """
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.info(f"📝 Step: {step_description}" + (f" | {context}" if context else ""))


def log_success(logger: logging.Logger, message: str, **kwargs):
    """
    Log a successful operation.
    
    Args:
        logger: Logger instance
        message: Success message
        **kwargs: Additional context
    """
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.info(f"✅ Success: {message}" + (f" | {context}" if context else ""))


def log_warning(logger: logging.Logger, message: str, **kwargs):
    """
    Log a warning with context.
    
    Args:
        logger: Logger instance
        message: Warning message
        **kwargs: Additional context
    """
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.warning(f"⚠️ Warning: {message}" + (f" | {context}" if context else ""))


def log_info(logger: logging.Logger, message: str, **kwargs):
    """
    Log informational message with context.
    
    Args:
        logger: Logger instance
        message: Info message
        **kwargs: Additional context
    """
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.info(f"ℹ️ Info: {message}" + (f" | {context}" if context else ""))


def log_api_execution(logger: logging.Logger):
    """
    Decorator to automatically log API execution steps.
    
    Usage:
        @log_api_execution(logger)
        def my_api_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(f"🚀 Starting API execution: {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ Completed API execution: {func_name}")
                return result
            except Exception as e:
                log_error(logger, e, f"During execution of {func_name}")
                raise
        return wrapper
    return decorator

