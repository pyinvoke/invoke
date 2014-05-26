from datetime import datetime
import os
import sys

exts = ('autodoc', 'intersphinx')# 'viewcode')
extensions = list(map(lambda x: 'sphinx.ext.%s' % x, exts))
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'Invoke'
year = datetime.now().year
copyright = u'%d Jeff Forcier' % year

# Ensure `links` try hitting API endpoints by default.
default_role = 'py:obj'
# And that we can talk to Python stdlib docs
intersphinx_mapping = {
    'python': ('http://docs.python.org/2.6', None),
}

# Ensure project directory is on PYTHONPATH for version, autodoc access
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))

exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'

# RTD stylesheet
html_style = 'rtd.css'
html_static_path = ['_static']

latex_documents = [
  ('index', 'invoke.tex', u'Invoke Documentation',
   u'Jeff Forcier', 'manual'),
]

# Autodoc settings
autodoc_default_flags = ['members']
autoclass_content = 'both'

# Releases for nice changelog, + settings
extensions.append('releases')
releases_release_uri = "https://github.com/pyinvoke/invoke/tree/%s"
releases_issue_uri = "https://github.com/pyinvoke/invoke/issues/%s"
