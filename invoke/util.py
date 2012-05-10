import logging


log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)
