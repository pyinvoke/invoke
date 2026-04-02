# Obtain shared config values
import os
import sys

sys.path.append(os.path.abspath(".."))
sys.path.append(os.path.abspath("../.."))
from shared_conf import *

# Enable autodoc, intersphinx
extensions.extend(["sphinx.ext.autodoc"])

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "special-members": True,
}

nitpick_ignore = {
    # stdlib, ref apparently broken w/ nothing I can do? not super relevant
    # anyway.
    ("py:class", "_frozen_importlib.ModuleSpec"),
    # Lexicon has no Sphinx doc site to cross-ref
    ("py:class", "Lexicon"),
    # Generic type T not worth documenting
    ("py:class", "invoke.tasks.T"),
}

# Sister-site links to WWW
html_theme_options["extra_nav_links"] = {
    "Main website": "https://www.pyinvoke.org"
}
