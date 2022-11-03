import asyncio
from functools import cached_property
import os
import sys
from typing import Any, Literal
from uuid import uuid4
import re
import os
import tempfile
from aiohttp import web
import base64
import time
import enum


SOURCES_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [SOURCES_ROOT] + sys.path

from logger import app_logger
from utils import now_str


class State(enum.Enum):
  start = 'Starting'
  fail = 'Failed'
  end = 'Finished'


routes = web.RouteTableDef()


@routes.view('/')
class PdfHanlder(web.View):
  count = 0

  def __init__(self, request: web.Request) -> None:
    super().__init__(request)
    self.start_time = time.perf_counter()

  async def post(self) -> web.StreamResponse:
    self._count_and_log(State.start)
    try:
      result = await self._handle()
      self._count_and_log(State.end)
      return result
    except:
      self._count_and_log(State.fail)
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

    if kind == State.start:
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

        pages_count = await self._wkhtmltopdf_exec(
          sourcefile.name,
          targetfile.name,
          options=json.get('options', {})
        )
        self._log(f'{pages_count} pages has been written', method='debug')

        size = 0

        while line := targetfile.read(8192):
          size += len(line)
          await response.write(line)

        self._log(f'{pages_count} bytes has been sent', method='debug')

        return response

  async def _wkhtmltopdf_exec(self, source: str, target: str, options: dict) -> int:
    args = ['wkhtmltopdf']
    if options:
      for option, value in options.items():
        args.append(f'--{option}')
        if value:
          args.append(f'{value}')

    args += [source, target]
    result = await self._cmd_exec(args)
    match = re.search(r'Loading pages \(\d+/(\d+)\)', result)
    assert(match)
    return int(match.group(1))

  async def _cmd_exec(self, cmd: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(
      *cmd,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
      env=os.environ
    )
    stdout, stderr = await proc.communicate()

    # wkhtmltopdf writes to stderr
    output = (stderr or stdout).decode()

    if (proc.returncode):
      raise Exception(output)

    return output


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
    print=run_app_print
  )
