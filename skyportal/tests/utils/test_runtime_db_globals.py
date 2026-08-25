"""The session factories init_db builds cannot be imported by name.

``async_plain_session_factory`` and its siblings are None until ``init_db``
assigns them, and the app imports every handler before the factory that calls
it. A module doing ``from baselayer.app.models import async_plain_session_factory``
therefore keeps None for the life of the process, and every use raises
``TypeError: 'NoneType' object is not callable``.

Nothing catches that at import, and the failure is quiet wherever the call sits
behind ``run_async``, which logs the exception and moves on. It is also invisible
to the rest of the suite: under pytest ``init_db`` has already run by the time a
module is imported, so the name binds to a real factory and the bug only appears
in the running app.

Import the module and read the attribute when it is needed:

    from baselayer.app import models as baselayer_models

    async with baselayer_models.async_plain_session_factory() as session:
        ...
"""

import ast
from pathlib import Path

# Assigned inside init_db (see its `global` statement in baselayer/app/models.py),
# so each is None at import time.
RUNTIME_GLOBALS = frozenset(
    {"async_engine", "async_session_factory", "async_plain_session_factory"}
)

PACKAGE = Path(__file__).resolve().parents[2]


def module_level_imports(path):
    """``(line, name)`` for each runtime global imported by name at module level.

    Only the module body is walked. The same import inside a function runs after
    init_db and is safe, which is why it is not reported.
    """
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.ImportFrom) and node.module == "baselayer.app.models":
            for alias in node.names:
                if alias.name in RUNTIME_GLOBALS:
                    yield node.lineno, alias.name


def test_runtime_globals_are_not_imported_by_name():
    offenders = [
        f"  {path.relative_to(PACKAGE.parent)}:{line} imports {name}"
        for path in sorted(PACKAGE.rglob("*.py"))
        for line, name in module_level_imports(path)
    ]
    assert not offenders, (
        "These modules bind a session factory at import time, when it is still "
        "None:\n"
        + "\n".join(offenders)
        + "\n\nImport `from baselayer.app import models as baselayer_models` and "
        "read the attribute where it is used instead."
    )
