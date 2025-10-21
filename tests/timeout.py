from typing import Any, Optional

import sys

import pytest
import invoke.context


try:
    from dataclasses import dataclass
    @dataclass
    class Result:
        """
        Result object that tells you why the process fails, if it failed.
        """
        stdout: str
        stderr: str
        returncode: Optional[int] = 0
        failure: Optional[str] = None
except ImportError:
    Result = object


def _run(**kwargs:Any) -> Result:
    """
    Minimal wrapper arround invoke.run() that encapsulate normal runs and errors into a single Result object.
    """
    process_result: Result
    try:
        _context = invoke.context.Context()
        result = _context.run(**kwargs)
        process_result = Result(stdout=result.stdout, stderr=result.stderr)

    except invoke.exceptions.CommandTimedOut as err:
      process_result = Result(stdout=err.result.stdout, 
            stderr=err.result.stderr,
            returncode=None, 
            failure=f"Command timed out after {kwargs.get('timeout')} seconds.")

    except invoke.exceptions.UnexpectedExit as err:
      process_result = Result(stdout=err.result.stdout, 
            stderr=err.result.stderr,
            returncode=err.result.exited, 
            failure=f"Command encountered a bad exit code: {err.result.exited}.")

    return process_result

@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.7 or higher (dataclasses)")
@pytest.mark.parametrize('runargs', 
    [dict(pty=True), dict(pty=False)],)
def test_timeout_1s(runargs) -> None:
    """
    Test for issue https://github.com/pyinvoke/invoke/issues/851
    """
    r = _run(command='\n'.join(
        ["ping -c 5 localhost", 
         "echo 'Done'"]), timeout=1, **runargs)
    assert r.failure == "Command timed out after 1 seconds."
    # Ensures no more than 5 lines got printed.
    lines = list(l for l in r.stdout.split('\n') if l.strip('\r\t '))
    assert len(lines) < 5, r.stdout
