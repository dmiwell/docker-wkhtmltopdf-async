import asyncio
import os
import re
import tempfile
from dataclasses import dataclass

RE_CMD_RESULT = re.compile(r'Loading pages \(\d+/(\d+)\)')
TMP_DIR = tempfile.gettempdir()


@dataclass
class CmdResult:
  pages: int
  rss: float


class CmdExecutor:
  @classmethod
  async def make_pdf(cls, source: str, target: str, options: dict) -> int:
    args = ['wkhtmltopdf']
    if options:
      for option, value in options.items():
        args.append(f'--{option}')
        if value:
          args.append(f'{value}')

    args += [source, target]
    result = await cls.exec(args)
    return cls._parse_pdf_result(result)

  @classmethod
  async def remove_junk_tmp_files(cls, dir: str, minutes_ago: int) -> int:
    result = await CmdExecutor.exec([
      'find', dir,
      '-type', 'f',
      '-mmin', f'+{minutes_ago}',
      '-print',
      '-delete'
    ])

    return len(result.split('\n')) if result else 0

  @classmethod
  async def exec(cls, cmd: list[str]) -> str:
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

  @classmethod
  def _parse_pdf_result(cls, result: str) -> int:
    match = RE_CMD_RESULT.search(result)
    if not match:
      raise Exception(f'Unable to parse result:/n{result}')

    return int(match.group(1))
