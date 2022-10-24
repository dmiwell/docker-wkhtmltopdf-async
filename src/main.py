import os
import sys
from typing import Any
import pdfkit
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

  @property
  def _log_extra(self) -> dict[str, object]:
    data: Any = self.request.headers.get('X-Log-Extra', {})
    assert(isinstance(data, dict))
    return data

  def _count_and_log(self, kind: State) -> None:
    extra: dict[str, object] = dict()
    if kind == State.start:
      PdfHanlder.count += 1
    else:
      extra['elapsed'] = self._total_time
      PdfHanlder.count -= 1
    extra['tasks_in_process'] = self.count

    app_logger.info(f'{kind.value} converting html to pdf', extra=dict(**self._log_extra, **extra))

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

        await pdfkit.from_file(
          sourcefile.name,
          targetfile.name,
          options=json.get('options', {})
        )

        while line := targetfile.read(1024):
          await response.write(line)

        return response


app = web.Application()
app.add_routes(routes)


if __name__ == '__main__':
  web.run_app(app, keepalive_timeout=300)
