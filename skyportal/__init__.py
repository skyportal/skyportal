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
    import math

    import numpy as np
    from psycopg2.extensions import AsIs, register_adapter

    def _adapt_numpy_float(val):
        f = float(val)
        if math.isnan(f):
            return AsIs("'NaN'::float")
        if math.isinf(f):
            return AsIs("'%s'::float" % ("Infinity" if f > 0 else "-Infinity"))
        return AsIs(repr(f))

    def _adapt_numpy_int(val):
        return AsIs(int(val))

    for _np_type in [np.float64, np.float32]:
        register_adapter(_np_type, _adapt_numpy_float)
    for _np_type in [np.int64, np.int32]:
        register_adapter(_np_type, _adapt_numpy_int)
    register_adapter(np.bool_, lambda val: AsIs("true" if val else "false"))
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
