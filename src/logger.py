from dataclasses import asdict
import logging
from typing import Any
from pythonjsonlogger import jsonlogger
from datetime import datetime
import os
from utils import md5_hash, memory_info_mb


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class CustomJsonFormatter(jsonlogger.JsonFormatter):
 def add_fields(
    self,
    log_record: dict[str, Any],
    record: logging.LogRecord,
    message_dict: dict[str, Any]
  ) -> None:
  super().add_fields(log_record, record, message_dict)

  log_record['level'] = record.levelno

  if (exc_info := log_record.get('exc_info', None)) and isinstance(exc_info, str):
    log_record['err_id'] = md5_hash(exc_info)

  if not log_record.get('timestamp'):
    log_record['timestamp'] = datetime.utcnow()

  for key in ('name',):
    if (value := getattr(record, key, None)) and value != 'root':
      log_record[key] = value

  log_record['mem'] = asdict(memory_info_mb())

log_handler = logging.StreamHandler()
formatter = CustomJsonFormatter()
log_handler.setFormatter(formatter)


app_logger = logging.getLogger()
app_logger.setLevel(getattr(logging, LOG_LEVEL))
app_logger.addHandler(log_handler)
