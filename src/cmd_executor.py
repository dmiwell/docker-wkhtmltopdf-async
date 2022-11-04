import asyncio
from dataclasses import dataclass
import os
import re


RE_CMD_RESULT = re.compile(r'Loading pages \(\d+/(\d+)\)')


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
    result = await cls._cmd_exec(args)
    return cls._parse_pdf_result(result)

  @classmethod
  def _parse_pdf_result(cls, result: str) -> int:
    match = RE_CMD_RESULT.search(result)
    if not match:
      raise Exception(f'Unable to parse result:/n{result}')

    return int(match.group(1))

  @classmethod
  async def _cmd_exec(cls, cmd: list[str]) -> str:
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
