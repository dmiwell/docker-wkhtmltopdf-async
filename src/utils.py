from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import md5
import sys
from typing import Final
from datetime import datetime
import resource
import psutil


DATETIME_FORMAT = '%Y%m%d_%H%M%S'
IS_DARWIN_OS = sys.platform == 'darwin'


def md5_hash(data: bytes | str) -> str:
  data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
  return md5(data_bytes).hexdigest()


def now_str() -> str:
  return datetime.utcnow().strftime(DATETIME_FORMAT)


@dataclass()
class MemoryInfo():
  sys_used: float
  sys_percent: float
  proc: float


def rusage_to_mb(rusage: float | int) -> float:
  factor = 1024 ** 2 if IS_DARWIN_OS else 1024
  return round((rusage / factor), 2)


def to_mb(number: int) -> float:
  return round((number / 1024 ** 2), 2)


def memory_info_mb() -> MemoryInfo:
  sys_memory = psutil.virtual_memory()
  proc_memory_rusage = resource.getrusage(resource.RUSAGE_SELF)


  return MemoryInfo(
    sys_used=to_mb(sys_memory.used),
    sys_percent=sys_memory.percent,
    proc=rusage_to_mb(proc_memory_rusage.ru_maxrss),
  )
