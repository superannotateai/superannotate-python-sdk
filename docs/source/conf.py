import os
import sys

sys.path.insert(0, os.path.abspath('../../src'))

# -- Project information -----------------------------------------------------

project = 'SuperAnnotate Python SDK'
copyright = '2021, SuperAnnotate AI'
author = 'SuperAnnotate AI'

# The full version, including alpha/beta/rc tags
from superannotate import __version__

release = __version__

# -- General configuration ---------------------------------------------------
master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc']


extensions += ['sphinx_inline_tabs']
extensions += ['jaraco.tidelift']
extensions += ['notfound.extension']


exclude_patterns = []

autodoc_typehints = "description"

html_show_sourcelink = False

html_static_path = ['images']
html_context = {
    "display_github": False,  # Add 'Edit on Github' link instead of 'View page source'
    "last_updated": True,
    "commit": False,
}

html_theme = 'furo'
html_logo = "images/sa_logo.png"

html_theme_options = {
    "sidebar_hide_name": True,
    "light_css_variables": {
        "color-brand-primary": "#336790",  # "blue"
        "color-brand-content": "#336790",
    },
    "dark_css_variables": {
        "color-brand-primary": "#E5B62F",  # "yellow"
        "color-brand-content": "#E5B62F",
    },
}
