from datetime import datetime
import os
import sys

exts = ('autodoc',)# 'viewcode')
extensions = map(lambda x: 'sphinx.ext.%s' % x, exts)
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'Invoke'
year = datetime.now().year
copyright = u'%d Jeff Forcier' % year

# Ensure `links` try hitting API endpoints by default.
default_role = 'py:obj'

# Ensure project directory is on PYTHONPATH for version, autodoc access
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))

exclude_trees = ['_build']
default_role = 'obj'
pygments_style = 'sphinx'
html_theme = 'default'

# RTD stylesheet
html_style = 'rtd.css'
html_static_path = ['_static']

latex_documents = [
  ('index', 'Invoke.tex', u'Invoke Documentation',
   u'Jeff Forcier', 'manual'),
]

# Autodoc settings
autodoc_default_flags = ['members']
