__version__ = "1.4.0"

try:
    # Once the IERS_Auto predictive values age past auto_max_age (30 days),
    # astropy re-downloads the table on every time/coordinate calculation and
    # raises if that fails - stalling request handlers for minutes before
    # erroring. Disable the age check; the sub-arcsecond drift on stale tables
    # does not matter for observability calculations.
    from astropy.utils.iers import conf as iers_conf

    iers_conf.auto_max_age = None

    # Monkey-patch matplotlib for simsurvey compatibility with matplotlib >= 3.8
    # simsurvey imports matplotlib.docstring which was renamed to matplotlib._docstring
    import matplotlib

    if not hasattr(matplotlib, "docstring"):
        matplotlib.docstring = matplotlib._docstring

    # Register numpy types with psycopg (v3) for numpy 2.x compatibility.
    # numpy 2 scalars no longer inherit from Python builtins, so psycopg's
    # default lookup misses them. Each dumper coerces the numpy scalar to
    # its native Python type and delegates to psycopg's built-in dumper,
    # which already handles NaN/Inf correctly.
    import numpy as np
    import psycopg
    from psycopg.types.bool import BoolDumper
    from psycopg.types.numeric import FloatDumper, Int8Dumper

    class _NumpyFloatDumper(FloatDumper):
        def dump(self, obj):
            return super().dump(float(obj))

    class _NumpyIntDumper(Int8Dumper):
        def dump(self, obj):
            return super().dump(int(obj))

    class _NumpyBoolDumper(BoolDumper):
        def dump(self, obj):
            return super().dump(bool(obj))

    for _np_type in [np.float64, np.float32]:
        psycopg.adapters.register_dumper(_np_type, _NumpyFloatDumper)
    for _np_type in [np.int64, np.int32]:
        psycopg.adapters.register_dumper(_np_type, _NumpyIntDumper)
    psycopg.adapters.register_dumper(np.bool_, _NumpyBoolDumper)
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
