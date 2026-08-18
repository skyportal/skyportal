#!/usr/bin/env python3
"""Check that the PyPI-published packages under projects/ agree on one version.

They release in lockstep, and uv drops the version specifier for workspace
sources (the lock records a bare `editable = ...`), so neither `uv lock` nor
`uv sync` notices a half-finished `uv version` bump. Published packages are
those under projects/ without the `Private :: Do Not Upload` classifier.
"""

import pathlib
import re
import sys
import tomllib

PRIVATE = "Private :: Do Not Upload"
PIN = re.compile(r"([A-Za-z0-9._-]+)\s*(==)?\s*([^\s,;]+)?")

root = pathlib.Path(__file__).resolve().parent.parent

published: dict[str, tuple[str, list[str], pathlib.Path]] = {}
for path in sorted(root.glob("projects/*/pyproject.toml")):
    project = tomllib.loads(path.read_text()).get("project", {})
    if PRIVATE in project.get("classifiers", []):
        continue
    published[project["name"]] = (
        project.get("version", "<dynamic>"),
        project.get("dependencies", []),
        path,
    )

versions = {name: version for name, (version, _, _) in published.items()}
errors = []

if len(set(versions.values())) > 1:
    listed = ", ".join(f"{n}={v}" for n, v in sorted(versions.items()))
    errors.append(f"published packages must share one version, got: {listed}")

for name, (_, deps, path) in published.items():
    rel = path.relative_to(root)
    for dep in deps:
        match = PIN.match(dep.strip())
        target = match.group(1)
        if target not in versions:
            continue
        if match.group(2) != "==":
            errors.append(f"{rel}: '{dep}' must pin {target} exactly (lockstep)")
        elif match.group(3) != versions[target]:
            errors.append(
                f"{rel}: pins {target}=={match.group(3)}, but it is {versions[target]}"
            )

for error in errors:
    print(f"error: {error}", file=sys.stderr)
if errors:
    print("\nBump every published package together, e.g.:", file=sys.stderr)
    for name in sorted(versions):
        print(f"  uv version --package {name} --bump minor", file=sys.stderr)
    print("then update the exact pins between them.", file=sys.stderr)
sys.exit(1 if errors else 0)
