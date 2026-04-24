__version__ = "1.4.0"

try:
    # Monkey-patch matplotlib for simsurvey compatibility with matplotlib >= 3.8
    # simsurvey imports matplotlib.docstring which was renamed to matplotlib._docstring
    import matplotlib

    if not hasattr(matplotlib, "docstring"):
        matplotlib.docstring = matplotlib._docstring

    # Register numpy types with psycopg2 for numpy 2.x compatibility
    # numpy 2 scalars no longer inherit from Python builtins, so psycopg2
    # needs explicit adapters to serialize them in SQL parameters
    import numpy as np
    from psycopg2.extensions import AsIs, register_adapter

    def _adapt_numpy_scalar(val):
        return AsIs(repr(float(val)))

    for _np_type in [np.float64, np.float32, np.int64, np.int32, np.bool_]:
        register_adapter(_np_type, _adapt_numpy_scalar)
except ImportError:
    # if the packages to monkey-patch are not available, just skip the patching
    pass

if "dev" in __version__:
    # Append last commit date and hash to dev version information, if available

    import os.path
    import subprocess

    try:
        p = subprocess.Popen(
            ["git", "log", "-1", '--format="%h %aI"'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(__file__),
        )
    except FileNotFoundError:
        pass
    else:
        out, err = p.communicate()
        if p.returncode == 0:
            git_hash, git_date = (
                out.decode("utf-8")
                .strip()
                .replace('"', "")
                .split("T")[0]
                .replace("-", "")
                .split()
            )

            __version__ = "+".join(
                [tag for tag in __version__.split("+") if not tag.startswith("git")]
            )
            __version__ += f"+git{git_date}.{git_hash}"
