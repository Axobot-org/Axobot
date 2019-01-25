# Credits: mikeshardmind
# https://github.com/mikeshardmind/SinbadCogs/blob/v3/calculator/jailer.py
# Used 6/01/2018

import resource
import subprocess
import sys
import pathlib
import shlex
import functools
import asyncio
from discord.ext import commands


def setlimits(*, timeout: int = 60, memlimit: int = 5):
    resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
    mb_as_b = memlimit * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (mb_as_b, mb_as_b))


async def run_jailed(
    *, expr: str, timeout: int = 60, memlimit: int = 60, ctx: commands.Context
):

    file_str = str(pathlib.Path(__file__).parent / "jailed_calc.py")
    run_args = [sys.executable, file_str]
    run_args.extend(shlex.quote(expr).split())
    runstr = " ".join(run_args)
    prexec = functools.partial(setlimits, timeout=timeout, memlimit=memlimit)
    p = await asyncio.create_subprocess_shell(
        runstr, preexec_fn=prexec, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        _outs, errs = await p.communicate()
    except Exception:
        p.kill()
        _outs, errs = await p.communicate()

    outs = _outs.decode()

    #msgs = pagify(outs, delims=["\n", " ", ""], priority=True, shorten_by=20)
    msgs = [outs[:1950]]

    inputstr = "input: `{}`\noutput:".format(expr)
    if len(inputstr) > 1999:
        inputstr = "output for request (too large to view) from {}".format(
            ctx.author.mention
        )
    await ctx.send(inputstr)
    for x in msgs:
        await ctx.send("```python\n{}\n```".format(x))
    #await ctx.send_interactive(msgs, box_lang="py")
