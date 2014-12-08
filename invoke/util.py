import logging
import os


def enable_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(module)s: %(message)s",
    )

# Allow from-the-start debugging (vs toggled during load of tasks module) via
# shell env var.
if os.environ.get('INVOKE_DEBUG'):
    enable_logging()

# Add top level logger functions to global namespace. Meh.
log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)
