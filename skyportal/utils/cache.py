from pathlib import Path
import hashlib
import os
import time
import io
import numpy as np

from baselayer.log import make_log

log = make_log('cache')


def array_to_bytes(array):
    """Convert np.array-like object to bytes (for use w/ caching infrastructure).

    Parameters
    ----------
    array : list or numpy array-like object
        Object to be converted to bytes
    """
    b = io.BytesIO()
    np.save(b, array)
    return b.getvalue()


class Cache:
    def __init__(self, cache_dir, max_items=None, max_age=None):
        """
        Parameters
        ----------
        cache_dir : Path or str
            Path to cache.  Will be created if necessary.
        max_items : int, optional
            Maximum number of items ever held in the cache.  If
            unspecified, then the cache size is only controlled by
            `max_age`. If zero, caching will be disabled.
        max_age : int, optional
            Maximum age (in seconds) of an item in the cache before it
            gets removed.  If unspecified, the cache size is only
            controlled by `max_items`.
        """
        cache_dir = Path(cache_dir)
        if not cache_dir.is_dir():
            cache_dir.mkdir(parents=True, exist_ok=True)

        self._cache_dir = Path(cache_dir)
        self._max_items = max_items
        self._max_age = max_age

    def _hash_filename(self, filename):
        m = hashlib.md5()
        m.update(filename.encode('utf-8'))
        return self._cache_dir / f'{m.hexdigest()}'

    def __getitem__(self, name):
        """Return item from the cache.

        Parameters
        ----------
        name : str
        """
        self.clean_cache()
        if name is None:
            return None

        # Cache is disabled, return nothing
        if self._max_items == 0:
            return None

        cache_file = self._hash_filename(name)
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

        fn = self._hash_filename(name)
        with open(fn, 'wb') as f:
            f.write(data)

        log(f"save [{name}] to [{os.path.basename(fn)}]")

        self.clean_cache()

    def _remove(self, filenames):
        """Remove given items from the cache.

        Parameters
        ----------
        filenames : list of str
            Files to remove from the cache.
        """
        # fmt: off
        for f in filenames:
            try:
                os.remove(f)
                log(f'cleanup [{os.path.basename(f)}]')
            except FileNotFoundError:
                pass
        # fmt: on

    def clean_cache(self):
        # Remove stale cache files
        cached_files = [
            (f.stat().st_mtime, f.absolute()) for f in self._cache_dir.glob('*')
        ]
        cached_files = sorted(cached_files, key=lambda x: x[0], reverse=True)

        now = time.time()

        if self._max_age is not None:
            removed_by_time = [
                filename
                for (mtime, filename) in cached_files
                if (now - mtime) > self._max_age
            ]
            self._remove(removed_by_time)

        if self._max_items is not None:
            oldest = cached_files[self._max_items :]
            self._remove([filename for (mtime, filename) in oldest])

    def __len__(self):
        return len(list(self._cache_dir.glob('*')))
