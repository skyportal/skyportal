__version__ = '0.9.dev0'

if 'dev' in __version__:
    import subprocess
    p = subprocess.Popen(['git', '--version'], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if 'git version' in out.decode('utf-8'):
        p = subprocess.Popen(['git', 'log', '-1', '--format="%h %aI"'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        out = out.decode('utf-8').strip().replace('"', '').split('T')[0].replace('-', '')
        if len(out.split()) == 2:
            git_hash, git_date = out.split()
            __version__ += f'+git{git_date}.{git_hash}'
