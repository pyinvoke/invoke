import os
import shutil
import time
from os.path import join

from invocations import docs as _docs
from invocations.testing import test
from invocations.packaging import vendorize, release

from invoke import ctask as task, run, Collection, Context


d = 'sites'

# Usage doc/API site (published as docs.paramiko.org)
docs_path = join(d, 'docs')
docs_build = join(docs_path, '_build')
docs = Collection.from_module(_docs, name='docs', config={
    'sphinx.source': docs_path,
    'sphinx.target': docs_build,
})

# Main/about/changelog site ((www.)?paramiko.org)
www_path = join(d, 'www')
www = Collection.from_module(_docs, name='www', config={
    'sphinx.source': www_path,
    'sphinx.target': join(www_path, '_build'),
})


@task
def vendorize_pexpect(ctx, version):
    target = 'invoke/vendor'
    package = 'pexpect'
    vendorize(
        distribution="pexpect-u",
        package=package,
        version=version,
        vendor_dir=target,
        license='LICENSE', # TODO: autodetect this in vendorize
    )
    # Nuke test dir inside package hrrgh
    shutil.rmtree(os.path.join(target, package, 'tests'))

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
    Builds both doc sites w/ maxed nitpicking.
    """
    # Turn warnings into errors, emit warnings about missing references.
    # This gives us a maximally noisy docs build.
    # Also enable tracebacks for easier debuggage.
    opts = "-W -n -T"
    # This is super lolzy but we haven't actually tackled nontrivial in-Python
    # task calling yet, so...
    docs_c, www_c = Context(config=c.config.clone()), Context(config=c.config.clone())
    docs_c.update(**docs.configuration())
    www_c.update(**www.configuration())
    docs['build'](docs_c, opts=opts)
    www['build'](www_c, opts=opts)


@task
def watch(c):
    """
    Watch both doc trees & rebuild them if files change.

    This includes e.g. rebuilding the API docs if the source code changes;
    rebuilding the WWW docs if the README changes; etc.
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import RegexMatchingEventHandler
    except ImportError:
        sys.exit("If you want to use this, 'pip install watchdog' first.")

    class APIBuildHandler(RegexMatchingEventHandler):
        def on_any_event(self, event):
            my_c = Context(config=c.config.clone())
            my_c.update(**docs.configuration())
            docs['build'](my_c)

    class WWWBuildHandler(RegexMatchingEventHandler):
        def on_any_event(self, event):
            my_c = Context(config=c.config.clone())
            my_c.update(**www.configuration())
            www['build'](my_c)

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

    # Run observer loop
    observer = Observer()
    # TODO: Find parent directory of tasks.py and use that.
    for x in (www_handler, api_handler):
        observer.schedule(x, '.', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


ns = Collection(
    test, integration, vendorize, release, www, docs, sites, vendorize_pexpect,
    watch
)
