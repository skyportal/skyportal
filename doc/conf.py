import os
import re
import sys
import warnings

import eralchemy2

sys.path.insert(0, os.path.abspath(".."))

# ligo.skymap, imported transitively below, warns about a private reproject module.
warnings.filterwarnings(
    "ignore", message=".*reproject.healpix.utils is a private module.*"
)

from skyportal import models  # noqa

extensions = [
    "recommonmark",
    "sphinx.ext.mathjax",
    "sphinx.ext.autosummary",
    "numpydoc",
]

# numpydoc emits an autosummary `:toctree:` per class member; without it Sphinx
# asks for stub files that are never generated.
numpydoc_class_members_toctree = False

# Inherited members pull third-party docstrings in, along with their unresolvable
# :ref: targets.
numpydoc_show_inherited_class_members = False

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"

project = "skyportal"
copyright = "2020–2023, The SkyPortal Team"
author = "The SkyPortal Team"

version = "vUndefined"
setup_lines = open("../skyportal/__init__.py").readlines()
for line in setup_lines:
    if line.startswith("__version__ = "):
        try:
            version = line.split('"')[1]
        except IndexError:
            version = line.split("'")[1]
        break

release = version

language = "en"

exclude_patterns = ["_build", "papers"]

pygments_style = "sphinx"

on_rtd = os.environ.get("READTHEDOCS", None) == "True"
if not on_rtd:
    import sphinx_book_theme  # noqa

    html_theme = "sphinx_book_theme"

html_static_path = ["_static"]

html_show_sourcelink = False

# create entity relationship diagram for skyportal
erd_path = os.path.join(os.path.dirname(__file__), "images/erd.svg")
erd_tables = [
    t for t in models.Base.metadata.tables if not re.search(r"_\d{4}_\d{2}$", t)
]
eralchemy2.render_er(models.Base, erd_path, include_tables=erd_tables)

with open(erd_path) as f:
    erd_svg = f.read()
with open(erd_path, "w") as f:
    f.write(re.sub(r'(<svg)\s+width="[^"]*"\s+height="[^"]*"', r"\1", erd_svg, count=1))


def setup(app):
    app.add_css_file("output_cells.css")
