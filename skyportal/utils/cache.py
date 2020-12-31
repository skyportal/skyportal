from pathlib import Path
import hashlib
import os

from baselayer.log import make_log

log = make_log('cache')


class Cache:
    def __init__(self, cache_dir, max_items=10):
        """
        Parameters
        ----------
        cache_dir : Path or str
            Path to cache.  Will be created if necessary.
        max_items : int, optional
            Maximum number of items ever held in the cache.
        """
        cache_dir = Path(cache_dir)
        if not cache_dir.is_dir():
            cache_dir.mkdir(parents=True, exist_ok=True)

        self._cache_dir = Path(cache_dir)
        self._max_items = max_items

    def _hash_fn(self, fn):
        m = hashlib.md5()
        m.update(fn.encode('utf-8'))
        return self._cache_dir / f'{m.hexdigest()}'

    def __getitem__(self, name):
        """Return item from the cache.

        Parameters
        ----------
        name : str
        """
        # Cache is disabled, return nothing
        if self._max_items == 0:
            return None

        cache_file = self._hash_fn(name)
        if not cache_file.exists():
            return None

        log(f"hit [{name}]")
        cache_file.touch()  # Make newest in cache

        return cache_file

    def __setitem__(self, name, data):
        """Insert item into cache.

        Parameters
        ----------
        name : str
            Name for this entry.
        data : bytes
            Bytes to be written to file associated with this entry.
        """
        # Cache is disabled, do not add entry
        if self._max_items == 0:
            return

        fn = self._hash_fn(name)
        with open(fn, 'wb') as f:
            f.write(data)

        log(f"save [{name}] to [{os.path.basename(fn)}]")

        self.clean_cache()

    def clean_cache(self):
        # Remove stale cache files
        cached_files = [
            (f.stat().st_mtime, f.absolute()) for f in self._cache_dir.glob('*')
        ]
        cached_files = sorted(cached_files, key=lambda x: x[0], reverse=True)
        # fmt: off
        for t, f in cached_files[self._max_items:]:
            try:
                os.remove(f)
                log(f'cleanup [{os.path.basename(f)}]')
            except FileNotFoundError:
                pass
        # fmt: on

    def __len__(self):
        return len(list(self._cache_dir.glob('*')))
