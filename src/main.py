import base64
import enum
import os
import sys
import tempfile
import time
from functools import cached_property
from typing import Any, Literal
from uuid import uuid4

from aiohttp import web

SOURCES_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [SOURCES_ROOT] + sys.path

from cmd_executor import CmdExecutor
from logger import app_logger
from utils import now_str, to_mb


class State(enum.Enum):
  START = 'Starting'
  FAILE = 'Failed'
  END = 'Finished'


routes = web.RouteTableDef()


@routes.view('/')
class PdfHanlder(web.View):
  count = 0

  def __init__(self, request: web.Request) -> None:
    super().__init__(request)
    self.start_time = time.perf_counter()

  async def post(self) -> web.StreamResponse:
    self._count_and_log(State.START)
    try:
      result = await self._handle()
      self._count_and_log(State.END)
      return result
    except:
      self._count_and_log(State.FAILE)
      raise

  @property
  def _total_time(self) -> float:
    return time.perf_counter() - self.start_time

  def _log(self, message: str, extra: dict[str, object] = dict(),
           method: Literal['info', 'warn', 'error', 'debug'] = 'info') -> None:
    getattr(app_logger, method)(message, extra=dict(**self._log_extra, **extra))

  @cached_property
  def _log_extra(self) -> dict[str, object]:
    return dict(trace_id=self.request.headers.get('X-Trace-Id', str(uuid4())))

  def _count_and_log(self, kind: State) -> None:
    extra: dict[str, object] = dict()

    if kind == State.START:
      PdfHanlder.count += 1
    else:
      extra['elapsed'] = self._total_time
      PdfHanlder.count -= 1

    extra['tasks_in_process'] = PdfHanlder.count

    self._log(f'{kind.value} converting html to pdf', extra)

  async def _handle(self) -> web.StreamResponse:
    json = await self.request.json()
    prefix = f'wkhtmltopdf.{now_str()}.'
    with tempfile.NamedTemporaryFile(prefix=prefix, suffix='.html') as sourcefile:
      sourcefile.write(base64.b64decode(json['contents']))
      sourcefile.flush()

      with tempfile.NamedTemporaryFile(prefix=prefix, suffix='.pdf') as targetfile:
        response = web.StreamResponse()
        response.content_type = 'application/pdf'
        await response.prepare(self.request)

        start = time.perf_counter()
        pages_num = await CmdExecutor.make_pdf(
          sourcefile.name,
          targetfile.name,
          options=json.get('options', {})
        )
        elapsed_pdf = time.perf_counter() - start

        size = 0

        start = time.perf_counter()
        while line := targetfile.read(8192):
          size += len(line)
          await response.write(line)

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

  web.run_app(
    app,
    port=80,
    keepalive_timeout=int(os.getenv('KEEPALIVE_TIMEOUT', 300)),
    shutdown_timeout=60,
    print=run_app_print,
  )
