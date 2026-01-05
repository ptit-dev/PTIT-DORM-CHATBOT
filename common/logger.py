import logging
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
import os


class VietnamFormatter(logging.Formatter):
    
    def format(self, record):
        vietnam_tz = timezone(timedelta(hours=7))
        timestamp = datetime.now(vietnam_tz).strftime('%Y-%m-%d %H:%M:%S')
        message = record.getMessage()
        
        if record.levelname in ['WARNING', 'ERROR']:
            return f"[{timestamp}] {record.levelname}: {message}"
        else:
            return f"[{timestamp}] {message}"


def setup_logger(name: str = 'app'):
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    os.makedirs('logs', exist_ok=True)
    
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(VietnamFormatter())
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(VietnamFormatter())
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
