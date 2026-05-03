import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Initializes the JSON logging matrix."""
    logger = logging.getLogger("med_core")
    
    # We do not care about debug spam in production. INFO and above only.
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate logs if the logger is called multiple times
    if logger.handlers:
        return logger

    logHandler = logging.StreamHandler()
    
    # The JSON schema. Every log will guarantee these fields exist.
    formatter = jsonlogger.JsonFormatter( # type: ignore
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ" # Strict ISO 8601 formatting
    )
    
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    
    return logger

# Expose a singleton instance
logger = setup_logging()