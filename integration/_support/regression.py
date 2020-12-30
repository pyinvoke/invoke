"""
Barebones regression-catching script that looks for ephemeral run() failures.

Intended to be run from top level of project via ``inv regression``. In an
ideal world this would be truly part of the integration test suite, but:

- something about the outer invoke or pytest environment seems to prevent such
  issues from appearing reliably (see eg issue #660)
- it can take quite a while to run, even compared to other integration tests.
"""


import sys

from invoke import task


@task
def check(c):
    count = 0
    failures = []
    for _ in range(0, 1000):
        count += 1
        try:
            # 'ls' chosen as an arbitrary, fast-enough-for-looping but
            # does-some-real-work example (where eg 'sleep' is less useful)
            response = c.run("ls", hide=True)
            if not response.ok:
                failures.append(response)
        except Exception as e:
            failures.append(e)
    if failures:
        print("run() FAILED {}/{} times!".format(len(failures), count))
        sys.exit(1)
