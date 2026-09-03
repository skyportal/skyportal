import json
import os
import re
import sys
import tempfile
import warnings

import eralchemy2
import pygraphviz

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
erd_dir = os.path.dirname(__file__)
erd_tables = [
    t for t in models.Base.metadata.tables if not re.search(r"_\d{4}_\d{2}$", t)
]
with tempfile.TemporaryDirectory() as erd_tmp:
    erd_dot_path = os.path.join(erd_tmp, "erd.dot")
    eralchemy2.render_er(models.Base, erd_dot_path, include_tables=erd_tables)
    with open(erd_dot_path) as f:
        erd_dot = f.read()

erd_enums = {}
for erd_name in erd_tables:
    for erd_column in models.Base.metadata.tables[erd_name].columns:
        rendered = str(erd_column.type)
        if len(rendered) <= 60:
            continue
        inner = getattr(erd_column.type, "item_type", erd_column.type)
        values = list(getattr(inner, "enums", None) or [])
        kind = type(erd_column.type).__name__
        erd_enums[f"{erd_name}.{erd_column.name}"] = values
        erd_dot = erd_dot.replace(f"[{rendered}]", f"[{kind} ({len(values)} values)]")

with open(os.path.join(erd_dir, "erd-data.html"), "w") as f:
    payload = json.dumps(erd_enums).replace("<", "\\u003c")
    f.write(f"<script>window.ERD_ENUMS = {payload};</script>\n")

erd_graph = pygraphviz.AGraph(
    string=erd_dot.replace('CELLPADDING="4"', 'CELLPADDING="6"')
)
erd_graph.graph_attr.update(
    bgcolor="transparent",
    rankdir="TB",
    pack="true",
    packmode="array",
    nodesep="0.3",
    ranksep="0.8",
)
erd_graph.edge_attr.update(penwidth="1.1")
erd_svg = erd_graph.draw(format="svg", prog="dot").decode()

# erd.js sizes the diagram through the viewBox; a fixed width would pin it at 22000px.
erd_svg = re.sub(r'(<svg)\s+width="[^"]*"\s+height="[^"]*"', r"\1", erd_svg, count=1)
# database.rst inlines this file, so drop the XML prolog and DOCTYPE it cannot carry.
with open(os.path.join(erd_dir, "erd.svg"), "w") as f:
    f.write(erd_svg[erd_svg.index("<svg") :])


def setup(app):
    app.add_css_file("output_cells.css")
    app.add_css_file("erd.css")
    app.add_js_file("erd.js", loading_method="defer")
