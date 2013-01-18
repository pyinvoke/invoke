import logging
import os


# Allow from-the-start debugging via shell env var
if os.environ.get('INVOKE_DEBUG'):
    logging.basicConfig(level=logging.DEBUG)



log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)
