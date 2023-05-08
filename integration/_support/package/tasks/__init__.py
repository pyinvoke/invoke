from invoke import Collection

# Issue #934 (from #919) only seems to trigger on this style of 'from . import
# xxx' - a vanilla self-contained tasks/__init__.py is still fine!
from . import module

ns = Collection(module)
