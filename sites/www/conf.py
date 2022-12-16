# Obtain shared config values
import sys
import os
from os.path import abspath, join, dirname

sys.path.append(abspath(join(dirname(__file__), "..")))
from shared_conf import *

# Releases changelog extension
extensions.append("releases")
releases_github_path = "pyinvoke/invoke"

# Default is 'local' building, but reference the public docs site when building
# under RTD.
target = join(dirname(__file__), "..", "docs", "_build")
if os.environ.get("READTHEDOCS") == "True":
    target = "https://docs.pyinvoke.org/en/latest/"
intersphinx_mapping["docs"] = (target, None)

# Sister-site links to documentation
html_theme_options["extra_nav_links"] = {
    "Documentation": "https://docs.pyinvoke.org"
}
