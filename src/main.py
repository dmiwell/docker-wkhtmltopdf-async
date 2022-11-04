import base64
import enum
import math
import os
import sys
import tempfile
import time
from typing import Any, Literal
from uuid import uuid4

from aiohttp import web

SOURCES_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [SOURCES_ROOT] + sys.path

from cmd_executor import CmdExecutor
from logger import app_logger
from utils import now_str, to_mb

KEEPALIVE_SEC = int(os.getenv('KEEPALIVE_TIMEOUT', 300))
KEEPALIVE_MIN = math.floor(KEEPALIVE_SEC / 60) + 1
TMP_DIR = os.path.join(tempfile.gettempdir(), 'wkhtmltopdf')


class State(enum.Enum):
  START = 'Starting'
  FAIL = 'Failed'
  END = 'Finished'


routes = web.RouteTableDef()


@routes.view('/')
class PdfHanlder(web.View):
  def __init__(self, request: web.Request) -> None:
    super().__init__(request)
    self._start_time = time.perf_counter()
    self._trace_id = request.headers.get('X-Trace-Id', str(uuid4()))

  async def post(self) -> web.StreamResponse:
    await self._log_state(State.START)
    try:
      await self._cleanup_tmp_files()
      result = await self._handle()
      await self._log_state(State.END)
      return result
    except:
      await self._log_state(State.FAIL)
      raise

  @property
  def _total_time(self) -> float:
    return time.perf_counter() - self._start_time

  def _log(self, message: str, extra: dict[str, object] | None = None,
           method: Literal['info', 'warn', 'error', 'debug'] = 'info') -> None:
    getattr(app_logger, method)(message, extra=dict(**self._log_extra, **(extra or {})))

  @property
  def _log_extra(self) -> dict[str, object]:
    return dict(
      trace_id=self._trace_id,
      elapsed=self._total_time,
    )

  async def _log_state(self, kind: State) -> None:
    self._log(f'{kind.value} converting html to pdf')

  async def _cleanup_tmp_files(self):
    deleted = await CmdExecutor.remove_junk_tmp_files(TMP_DIR, KEEPALIVE_MIN)
    if (deleted):
      self._log(f'Deleted {deleted} garbage files')

  async def _handle(self) -> web.StreamResponse:
    json = await self.request.json()
    prefix = f'{now_str()}.'
    with tempfile.NamedTemporaryFile(prefix=prefix, suffix='.html', dir=TMP_DIR) as sourcefile:
      sourcefile.write(base64.b64decode(json['contents']))
      sourcefile.flush()

      with tempfile.NamedTemporaryFile(prefix=prefix, suffix='.pdf', dir=TMP_DIR) as targetfile:
        start = time.perf_counter()
        pages_num = await CmdExecutor.make_pdf(
          sourcefile.name,
          targetfile.name,
          options=json.get('options', {})
        )

        sourcefile.close()

        elapsed_pdf = time.perf_counter() - start


        response = web.StreamResponse()
        response.content_type = 'application/pdf'
        await response.prepare(self.request)

        start = time.perf_counter()
        size = 0
        while line := targetfile.read(8192):
          size += len(line)
          await response.write(line)

        targetfile.close()

        elapsed_download = time.perf_counter() - start
        self._log(
          f'{to_mb(size)} mb were sent. pdf with {pages_num} pages.',
          dict(
            elapsed_pdf=elapsed_pdf,
            elapsed_download=elapsed_download,
          )
        )

    return response


app = web.Application()
app.add_routes(routes)


if __name__ == '__main__':
  def run_app_print(arg: Any):
    if isinstance(arg, str):
     arg = arg.replace('(Press CTRL+C to quit)', '').strip()

    app_logger.info(arg)

  os.makedirs(TMP_DIR, mode=0o770, exist_ok=True)

  web.run_app(
    app,
    port=80,
    keepalive_timeout=KEEPALIVE_SEC,
    shutdown_timeout=60,
    print=run_app_print,
  )
