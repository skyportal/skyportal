from setuptools import setup

import locale
import os
import re
import subprocess
import warnings

from pathlib import Path
from skyportal import __version__


def _decode_stdio(stream):
    try:
        stdio_encoding = locale.getdefaultlocale()[1] or 'utf-8'
    except ValueError:
        stdio_encoding = 'utf-8'

    try:
        text = stream.decode(stdio_encoding)
    except UnicodeDecodeError:
        # Final fallback
        text = stream.decode('latin1')

    return text


def get_git_devstr(sha=False, show_warning=True, path=None):
    """
    Determines the number of revisions in this repository.
    Parameters
    ----------
    sha : bool
        If True, the full SHA1 hash will be returned. Otherwise, the total
        count of commits in the repository will be used as a "revision
        number".
    show_warning : bool
        If True, issue a warning if git returns an error code, otherwise errors
        pass silently.
    path : str or None
        If a string, specifies the directory to look in to find the git
        repository.  If `None`, the current working directory is used, and must
        be the root of the git repository.
        If given a filename it uses the directory containing that file.
    Returns
    -------
    devversion : str
        Either a string with the revision number (if `sha` is False), the
        SHA1 hash of the current commit (if `sha` is True), or an empty string
        if git version info could not be identified.
    """

    if path is None:
        path = os.getcwd()

    if not os.path.isdir(path):
        path = os.path.abspath(os.path.dirname(path))

    if sha:
        # Faster for getting just the hash of HEAD
        cmd = ['rev-parse', 'HEAD']
    else:
        cmd = ['rev-list', '--count', 'HEAD']

    def run_git(cmd):
        try:
            p = subprocess.Popen(['git'] + cmd, cwd=path,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            stdout, stderr = p.communicate()
        except OSError as e:
            if show_warning:
                warnings.warn('Error running git: ' + str(e))
            return (None, b'', b'')

        if p.returncode == 128:
            if show_warning:
                warnings.warn('No git repository present at {0!r}! Using '
                              'default dev version.'.format(path))
            return (p.returncode, b'', b'')
        if p.returncode == 129:
            if show_warning:
                warnings.warn('Your git looks old (does it support {0}?); '
                              'consider upgrading to v1.7.2 or '
                              'later.'.format(cmd[0]))
            return (p.returncode, stdout, stderr)
        elif p.returncode != 0:
            if show_warning:
                warnings.warn('Git failed while determining revision '
                              'count: {0}'.format(_decode_stdio(stderr)))
            return (p.returncode, stdout, stderr)

        return p.returncode, stdout, stderr

    returncode, stdout, stderr = run_git(cmd)

    if not sha and returncode == 128:
        # git returns 128 if the command is not run from within a git
        # repository tree. In this case, a warning is produced above but we
        # return the default dev version of '0'.
        return '0'
    elif not sha and returncode == 129:
        # git returns 129 if a command option failed to parse; in
        # particular this could happen in git versions older than 1.7.2
        # where the --count option is not supported
        # Also use --abbrev-commit and --abbrev=0 to display the minimum
        # number of characters needed per-commit (rather than the full hash)
        cmd = ['rev-list', '--abbrev-commit', '--abbrev=0', 'HEAD']
        returncode, stdout, stderr = run_git(cmd)
        # Fall back on the old method of getting all revisions and counting
        # the lines
        if returncode == 0:
            return str(stdout.count(b'\n'))
        else:
            return ''
    elif sha:
        return _decode_stdio(stdout)[:40]
    else:
        return _decode_stdio(stdout).strip()


# Need a recursive glob to find all package data files if there are
# subdirectories
import fnmatch


def recursive_glob(basedir, pattern):
    matches = []
    for root, dirnames, filenames in os.walk(basedir):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))
    return matches


# Set affiliated package-specific settings
PACKAGENAME = 'skyportal_models'
DESCRIPTION = 'Collaborative Platform for Time-Domain Astronomy'
LONG_DESCRIPTION = ''
AUTHOR = 'The Skyportal Developers'
AUTHOR_EMAIL = ''
LICENSE = 'BSD'
URL = 'skyportal.io'

# VERSION should be PEP386 compatible (http://www.python.org/dev/peps/pep-0386)
VERSION = __version__

# Indicates if this version is a release version
RELEASE = 'dev' not in VERSION

if not RELEASE:
    VERSION += get_git_devstr(sha=False)


# parse depenency versions from requirements.txt
deps = ['numpy',
        'scipy',
        'astropy',
        'sqlalchemy-utils',
        'marshmallow',
        'marshmallow-sqlalchemy',
        'marshmallow-enum',
        'simplejson',
        'arrow',
        'tornado',
        'sncosmo']


# these are where the version numbers of the dependencies can be found
reqfiles = map(lambda f: Path(__file__).parent / f, [
    'requirements.txt',
    'baselayer/requirements.txt'
])

depdict = {}
for r in reqfiles:
    with open(r, 'r') as f:
        for line in f:
            line = line.strip()
            m = re.match('([^<=>]+).*', line)
            packagename = m.group(1)
            depdict[packagename] = line

# match the dependencies to their version numbers
deps = [depdict[dep] for dep in deps]


setup(name=PACKAGENAME,
      version=VERSION,
      description=DESCRIPTION,
      py_modules=['skyportal.models', 'skyportal.schema',
                  'skyportal.phot_enum',
                  'baselayer.__init__',
                  'baselayer.app.__init__',
                  'baselayer.app.models',
                  'baselayer.app.json_util',
                  'baselayer.app.custom_exceptions'],
      install_requires=deps,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      license=LICENSE,
      url=URL,
      long_description=LONG_DESCRIPTION
)
