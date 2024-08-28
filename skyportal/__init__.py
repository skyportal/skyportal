__version__ = '1.0.0'

if 'dev' in __version__:
    # Append last commit date and hash to dev version information, if available

    import subprocess
    import os.path

    try:
        p = subprocess.Popen(
            ['git', 'log', '-1', '--format="%h %aI"'],
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
                out.decode('utf-8')
                .strip()
                .replace('"', '')
                .split('T')[0]
                .replace('-', '')
                .split()
            )

            __version__ = '+'.join(
                [tag for tag in __version__.split('+') if not tag.startswith('git')]
            )
            __version__ += f'+git{git_date}.{git_hash}'
