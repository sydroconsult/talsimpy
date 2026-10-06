# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import talsimpy
# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'talsimpy'
copyright = '2026, Sydro Consult GmbH'
author = 'Sydro Consult GmbH'
release = talsimpy.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx', 
    'myst_parser',
]
myst_enable_extensions = ["colon_fence"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
myst_heading_anchors = 2
intersphinx_mapping = {
     "python": ("https://docs.python.org/3", None),
     "numpy": ("https://numpy.org/doc/stable/", None),
     "pandas": ("https://pandas.pydata.org/docs/", None),
 }

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
autoclass_content = "both"
autodoc_member_order = "bysource"
autodoc_typehints = "description"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
