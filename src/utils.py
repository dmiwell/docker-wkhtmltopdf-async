from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import md5
from typing import Final
from datetime import datetime
import resource
import psutil
import os


DATETIME_FORMAT: Final[str] = '%Y%m%d_%H%M%S'


@dataclass()
class MemoryInfo():
  sys_used: float
  sys_percent: float
  proc_used: float
  subproc_used: float


def md5_hash(data: bytes | str) -> str:
  data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
  return md5(data_bytes).hexdigest()


def now_str() -> str:
  return datetime.utcnow().strftime(DATETIME_FORMAT)


def memory_info() -> MemoryInfo:
  sys_memory = psutil.virtual_memory()
  proc_memory = resource.getrusage(resource.RUSAGE_SELF)
  child_memory = resource.getrusage(resource.RUSAGE_CHILDREN)
  return MemoryInfo(
    sys_used=sys_memory.used,
    sys_percent=sys_memory.percent,
    proc_used=proc_memory.ru_maxrss,
    subproc_used=child_memory.ru_maxrss,
  )


def memory_info_mb() -> MemoryInfo:
  os.getpid()
  memory = memory_info()
  memory_dict = asdict(memory)
  memory_dict.pop('sys_percent')
  return MemoryInfo(
    **{ k: round(v / 1024 ** 2, 2) for k, v in memory_dict.items() },
    sys_percent=memory.sys_percent,
  )
