from datetime import datetime
from os.path import abspath, join, dirname

import alabaster


# Alabaster theme + mini-extension
html_theme_path = [alabaster.get_path()]
extensions = ["alabaster", "sphinx.ext.intersphinx", "sphinx.ext.doctest"]
# Paths relative to invoking conf.py - not this shared file
html_theme = "alabaster"
html_theme_options = {
    "description": "Pythonic task execution",
    "github_user": "pyinvoke",
    "github_repo": "invoke",
    "analytics_id": "UA-18486793-3",
    "travis_button": False,  # No longer on Travis-CI; README buttons link to Circle
    "codecov_button": False,  # Now a README button
    "tidelift_url": "https://tidelift.com/subscription/pkg/pypi-invoke?utm_source=pypi-invoke&utm_medium=referral&utm_campaign=docs",  # noqa
}
html_sidebars = {
    "**": ["about.html", "navigation.html", "searchbox.html", "donate.html"]
}

# Everything intersphinx's to Python
intersphinx_mapping = {"python": ("https://docs.python.org/2.7/", None)}

# Doctest settings
doctest_path = [abspath(join(dirname(__file__), "..", "tests"))]
doctest_global_setup = r"""
from _util import MockSubprocess
"""

# Regular settings
project = "Invoke"
year = datetime.now().year
copyright = "{} Jeff Forcier".format(year)
master_doc = "index"
templates_path = ["_templates"]
exclude_trees = ["_build"]
source_suffix = ".rst"
default_role = "obj"
