import logging
from datetime import datetime
from pathlib import Path

_logger = None

def get_logger():
    """Get the application-wide logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger

def setup_logger(log_dir: str = "logs"):
    """Setup a logger that saves everything to a file."""
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"agent_{timestamp}.log"
    
    # Setup logger
    logger = logging.getLogger("agent")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler - saves everything to file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Simple formatter
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    logger.info(f"=== Agent session started ===")
    return logger


logger = get_logger()