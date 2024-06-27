import re
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

def get_version():
    """Extract Memoriam version string from the current pyproject.toml file"""
    pyproject = Path(__file__, '..', '..', 'pyproject.toml').resolve().read_text()
    match = re.search(r'version = "(.*?)"', pyproject)
    return match.group(1) if match else ''

project = 'Memoriam'
release = get_version()
copyright = '2022, Protojour AS'
author = 'Protojour dev team'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['myst_parser']
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_title = ' '
html_static_path = ['_static']
html_favicon = 'favicon.png'

html_css_files = [
    'style.css',
    'fonts/metropolis.css',
    'fonts/dejavu-sans-mono.css',
]

html_theme_options = {
    'light_logo': 'memoriam.svg',
    'dark_logo': 'memoriam_dark.svg',
    'light_css_variables': {
        'font-stack': 'Metropolis, sans-serif',
        'font-stack--monospace': 'DejaVu Sans Mono, monospace',
    },
}

pygments_style = 'monokai'
pygments_dark_style = 'monokai'

myst_heading_anchors = 3
