import sys
import time

from invocations.docs import docs, www
from invocations.testing import test, coverage
from invocations.packaging import vendorize, release

from invoke import ctask as task, Collection, Context
from invoke.util import LOG_FORMAT


@task(help=test.help)
def integration(c, module=None, runner=None, opts=None):
    """
    Run the integration test suite. May be slow!
    """
    opts = opts or ""
    opts += " --tests=integration/"
    test(c, module, runner, opts)


@task
def sites(c):
    """
    Build both doc sites w/ maxed nitpicking.
    """
    # Turn warnings into errors, emit warnings about missing references.
    # This gives us a maximally noisy docs build.
    # Also enable tracebacks for easier debuggage.
    opts = "-W -n -T"
    # This is super lolzy but we haven't actually tackled nontrivial in-Python
    # task calling yet, so...
    docs_c = Context(config=c.config.clone())
    www_c = Context(config=c.config.clone())
    docs_c.update(**docs.configuration())
    www_c.update(**www.configuration())
    docs['build'](docs_c, opts=opts)
    www['build'](www_c, opts=opts)



def make_handler(c, task_, regexes, ignore_regexes, *args, **kwargs):
    args = [c] + list(args)
    try:
        from watchdog.events import RegexMatchingEventHandler
    except ImportError:
        sys.exit("If you want to use this, 'pip install watchdog' first.")

    class Handler(RegexMatchingEventHandler):
        def on_any_event(self, event):
            try:
                task_(*args, **kwargs)
            except:
                pass

    return Handler(regexes=regexes, ignore_regexes=ignore_regexes)

def observe(*handlers):
    try:
        from watchdog.observers import Observer
    except ImportError:
        sys.exit("If you want to use this, 'pip install watchdog' first.")

    observer = Observer()
    # TODO: Find parent directory of tasks.py and use that.
    for handler in handlers:
        observer.schedule(handler, '.', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def watch(c, task_, regexes, ignore_regexes, *args, **kwargs):
    observe(make_handler(c, task_, regexes, ignore_regexes, *args, **kwargs))


@task
def watch_docs(c):
    """
    Watch both doc trees & rebuild them if files change.

    This includes e.g. rebuilding the API docs if the source code changes;
    rebuilding the WWW docs if the README changes; etc.
    """
    try:
        from watchdog.events import RegexMatchingEventHandler
    except ImportError:
        sys.exit("If you want to use this, 'pip install watchdog' first.")

    class APIBuildHandler(RegexMatchingEventHandler):
        def on_any_event(self, event):
            my_c = Context(config=c.config.clone())
            my_c.update(**docs.configuration())
            try:
                docs['build'](my_c)
            except:
                pass

    class WWWBuildHandler(RegexMatchingEventHandler):
        def on_any_event(self, event):
            my_c = Context(config=c.config.clone())
            my_c.update(**www.configuration())
            try:
                www['build'](my_c)
            except:
                pass

    # Readme & WWW triggers WWW
    www_handler = WWWBuildHandler(
        regexes=['\./README.rst', '\./sites/www'],
        ignore_regexes=['.*/\..*\.swp', '\./sites/www/_build'],
    )
    # Code and docs trigger API
    api_handler = APIBuildHandler(
        regexes=['\./invoke/', '\./sites/docs'],
        ignore_regexes=['.*/\..*\.swp', '\./sites/docs/_build'],
    )

    observe(www_handler, api_handler)


@task
def watch_tests(c, module=None):
    """
    Watch source tree and test tree for changes, rerunning tests as necessary.
    """
    watch(
        c, test, ['\./invoke/', '\./tests/'], ['.*/\..*\.swp'], module=module
    )


ns = Collection(
    test, coverage, integration, vendorize, release, www, docs, sites,
    watch_docs, watch_tests
)
ns.configure({
    'coverage': {'package': 'invoke'},
    'tests': {'logformat': LOG_FORMAT},
})
