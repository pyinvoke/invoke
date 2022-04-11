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
def test_timeout_1s() -> None:
    """
    Test for issue https://github.com/pyinvoke/invoke/issues/851
    """
    r = _run(command="set -euo pipefail\nping -c 10 localhost\necho 'Done'", 
             timeout=1, pty=True, in_stream=False, out_stream=sys.stderr, err_stream=sys.stderr, )
    assert r.failure == "Command timed out after 1 seconds."
    # Ensures no more than 10 lines got printed, for instance:
    # PING localhost (127.0.0.1): 56 data bytes
    # 64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.053 ms
    assert len(list(l for l in r.stdout.split('\n') if l.strip('\r\t '))) < 10, r.stdout
