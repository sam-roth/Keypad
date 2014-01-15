

import pathlib
import os
import tempfile
import contextlib


@contextlib.contextmanager
def write_atomically(path):
    

    path = pathlib.Path(path)
    
    tmpfd, tmpfile_name = tempfile.mkstemp(
        dir=path.parent.as_posix(),
        prefix=path.name,
        suffix='.swp',
        text=False
    )

    tmpfile_name = pathlib.Path(tmpfile_name)

    with open(tmpfd, 'wb') as f:
        yield f

        # Ensure nothing is stuck in the I/O buffer so that sync() will
        # work as expected.
        f.flush()

        # Sync the file to the disk, bypassing kernel-level I/O caching.
        os.fsync(f.fileno())


    # POSIX-compliant systems will perform this operation atomically.
    tmpfile_name.replace(path)

    

