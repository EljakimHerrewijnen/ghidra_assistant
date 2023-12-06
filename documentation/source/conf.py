# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Ghidra Assistant'
copyright = '2022, Eljakim Herrewijnen'
author = 'Eljakim Herrewijnen'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [  'myst_parser',
                'sphinx_rtd_theme',
                'sphinx.ext.todo',
                'sphinxcontrib.confluencebuilder',
                "sphinxcontrib.drawio",
]

templates_path = ['_templates']

include_patterns = ['**/device_docs', '**index.rst', '**/source', '*', 'architectures/*', 'emulator/*']
exclude_patterns = ['**/dump', '**/venv', '**/devices']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Settings for confluence
confluence_publish = True
confluence_space_key = 'DTSPHINX'
confluence_publish_root = 149522309 #Find in URL by editing a page
confluence_page_hierarchy = True
# confluence_publish_dryrun = True
confluence_server_url = 'https://confluence.dev.holmes.nl/'
confluence_ask_password = True
confluence_ask_user = True
confluence_prev_next_buttons_location = 'top'