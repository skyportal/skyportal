# Releasing Python packages

The packages under `projects/` that are published to PyPI release **in
lockstep**: one version, one tag, one changelog, one workflow run.

| directory       | distribution          |
| --------------- | --------------------- |
| `python-client` | `skyportal-py`        |
| `api-models`    | `skyportal-py-models` |

Versions are static and bumped with `uv version`; the `pypi-v*` tag marks the
release commit. Because `uv` drops the version specifier for workspace sources,
nothing in the normal `uv lock` / `uv sync` path notices a half-finished bump,
so `tools/check_published_versions.py` enforces it in pre-commit and again
before upload. SkyPortal's own application releases use plain `vX.Y.Z` tags (see
`RELEASE.txt`) and are unaffected.

All commands run inside the nix dev shell (`nix develop`), which provides uv.

## Cutting a release

1.  Bump every published package to the same new version, and update the exact
    pins between them (`skyportal-py` pins `skyportal-py-models`):

        uv version --package skyportal-py --bump minor
        uv version --package skyportal-py-models --bump minor

    Then confirm they agree:

        python3 tools/check_published_versions.py

2.  Preview the changelog:

    uv run --only-group dev towncrier build --draft --dir projects --version X.Y.Z

3.  Compile it. This inserts a section into `projects/CHANGES.md` and deletes
    the consumed fragments from `projects/changes.d/`:

        uv run --only-group dev towncrier build --dir projects --version X.Y.Z

4.  Commit and land on `main` (use the `skip-changelog` label if it goes through
    a pull request):

        git add -A && git commit -m "Release X.Y.Z"

5.  Tag the release commit and push:

    git tag pypi-vX.Y.Z
    git push origin main --tags

6.  Publish a GitHub release for the tag, pasting the new `CHANGES.md` section
    as the notes:

        gh release create pypi-vX.Y.Z --title "X.Y.Z"

    Publishing the GitHub release is what triggers the upload; a tag alone does
    nothing. The `publish-python.yaml` workflow refuses to continue unless every
    package's committed version matches the tag, then builds them all and
    uploads them together via trusted publishing.

7.  Verify both packages on PyPI and that the "Upload Python Packages" run is
    green.

## Adding another published package

1. Create it under `projects/` with a static `version` matching the other
   published packages, and no `Private :: Do Not Upload` classifier (that
   classifier is what marks a package as internal).
2. Add it to `workspace.members` in the root `pyproject.toml`.
3. Add its distribution name to `PACKAGES` in `publish-python.yaml`.
4. Register it as a PyPI trusted publisher pointing at `publish-python.yaml`.

`tools/check_published_versions.py` discovers it automatically and will require
it to move with the others.

No new tag series or changelog is needed: it joins the existing lockstep.

## Notes

`skyportal-py` pins `skyportal-py-models` exactly, since they always ship the
same version. The workspace source is stripped at build time, so the published
wheel carries a real `skyportal-py-models==X.Y.Z` requirement. Both wheels are
uploaded in a single call, so neither has to be released first.
