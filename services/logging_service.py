import logging
import os
import glob
import zipfile
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from typing import List
from pathlib import Path

class VietnamFormatter(logging.Formatter):
    
    def format(self, record: logging.LogRecord) -> str:
        vietnam_tz = timezone(timedelta(hours=7))
        timestamp = datetime.now(vietnam_tz).strftime('%Y-%m-%d %H:%M:%S')
        message = record.getMessage()
        
        module_name = record.name
        service_prefix = "SERVER"
        
        if "database" in module_name.lower() or "db" in module_name.lower():
            service_prefix = "DB"
        elif "rag" in module_name.lower():
            service_prefix = "RAG"
        elif "backend" in module_name.lower() or "api" in module_name.lower():
            service_prefix = "API"
        elif "websocket" in module_name.lower() or "chat" in module_name.lower():
            service_prefix = "WS"
        
        if record.levelname in ['WARNING', 'ERROR', 'CRITICAL']:
            return f"[{timestamp}] {service_prefix}: {record.levelname}: {message}"
        else:
            return f"[{timestamp}] {service_prefix}: {message}"


class LoggingService:
    
    def __init__(self):
        self._log_dir = "logs"
        self._log_file = "app.log"
        self._max_bytes = 10 * 1024 * 1024  # 10MB
        self._backup_count = 5
        self.logs_dir = Path(self._log_dir)
        self._setup_logging()
    
    def _setup_logging(self):
        os.makedirs(self._log_dir, exist_ok=True)
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        logger.handlers.clear()
        
        log_path = os.path.join(self._log_dir, self._log_file)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(VietnamFormatter())
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(VietnamFormatter())
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized: {log_path}")
    
    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)
    
    def get_log_file_path(self) -> str:
        return os.path.join(self._log_dir, self._log_file)
    
    def get_all_log_files(self) -> List[str]:
        log_pattern = os.path.join(self._log_dir, f"{self._log_file}*")
        log_files = glob.glob(log_pattern)
        log_files.sort(key=os.path.getmtime, reverse=True)
        return log_files
    
    def get_log_lines_from_time(self, minutes_ago: int = 5) -> List[str]:
        vietnam_tz = timezone(timedelta(hours=7))
        cutoff_time = datetime.now(vietnam_tz) - timedelta(minutes=minutes_ago)
        
        matching_lines = []
        log_files = self.get_all_log_files()
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('['):
                            try:
                                timestamp_str = line[1:20]
                                log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                log_time = log_time.replace(tzinfo=vietnam_tz)
                                
                                if log_time >= cutoff_time:
                                    matching_lines.append(line.rstrip('\n'))
                            except (ValueError, IndexError):
                                continue
            except Exception:
                continue
        
        return matching_lines
    
    def tail_log_file(self, num_lines: int = 100) -> List[str]:
        log_file = self.get_log_file_path()
        
        if not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return [line.rstrip('\n') for line in lines[-num_lines:]]
        except Exception:
            return []
    
    def get_log_files(self) -> List[str]:
        if not self.logs_dir.exists():
            return []
        
        log_files = []
        for file_path in self.logs_dir.glob("*.log"):
            log_files.append(str(file_path))
        
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return [Path(f).name for f in log_files]
    
    def get_latest_log_path(self) -> Path:
        log_files = self.get_log_files()
        if log_files:
            return self.logs_dir / log_files[0]
        return self.logs_dir / self._log_file
    
    def create_logs_archive(self, archive_name: str = "logs.zip") -> Path:
        archive_path = Path(archive_name)
        logger = self.get_logger(__name__)
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if self.logs_dir.exists():
                    for file_path in self.logs_dir.glob("*.log"):
                        zipf.write(file_path, arcname=file_path.name)
                        logger.info(f"Added {file_path.name} to archive")
            
            logger.info(f"Created logs archive: {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"Error creating logs archive: {str(e)}")
            raise
    
    def cleanup_temp_archive(self, archive_path: Path):
        logger = self.get_logger(__name__)
        try:
            if archive_path.exists():
                os.remove(archive_path)
                logger.info(f"Cleaned up temporary archive: {archive_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup archive: {str(e)}")