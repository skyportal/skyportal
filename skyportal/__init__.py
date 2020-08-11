__version__ = '0.9.dev0'

if 'dev' in __version__:
    # Append last commit date and hash to dev version information, if available

    import subprocess
    try:
        p = subprocess.Popen(['git', 'log', '-1', '--format="%h %aI"'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except FileNotFoundError:
        pass
    else:
        out, err = p.communicate()
        if p.returncode == 0:
            git_hash, git_date = (out.decode('utf-8').strip().replace('"', '')
                                 .split('T')[0].replace('-', '').split())

            __version__ += f'+git{git_date}.{git_hash}'
