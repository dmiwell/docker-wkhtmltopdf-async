from datetime import datetime
from hashlib import md5
from typing import Final
from datetime import datetime


DATETIME_FORMAT: Final[str] = '%Y%m%d_%H%M%S'


def md5_hash(data: bytes | str) -> str:
  data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
  return md5(data_bytes).hexdigest()


def now_str() -> str:
  return datetime.utcnow().strftime(DATETIME_FORMAT)
