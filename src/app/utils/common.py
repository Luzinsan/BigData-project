import logging
import os
import traceback


def setup_logger(
    name: str = __name__, 
    level: int = logging.INFO
) -> logging.Logger:
    """
    Logger setup
    
    Args:
        name (str): Logger name
        level (int): Logging level

    Returns:
        logger (logging.Logger): Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.hasHandlers():
        logging.basicConfig(
            level=level, 
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    return logger