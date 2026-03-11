try:
    # NumPy 2 removed np.float_; keep legacy code paths compatible.
    import numpy as np

    if "float_" not in np.__dict__:
        np.float64 = np.float64
except ImportError:
    pass

# similarly, matplotlib has removed the "matplotlib.docstring" attribute in version 3.10.8, so we add it back for compatibility with older versions of matplotlib
try:
    import matplotlib

    if not hasattr(matplotlib, "docstring"):
        matplotlib.docstring = lambda x: x
except ImportError:
    pass

__version__ = "1.4.0"

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
