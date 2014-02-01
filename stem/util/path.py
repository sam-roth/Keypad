

import pathlib
import glob


def search_upwards(path, glob):
    path = pathlib.Path(path)
    while path is not None:
        yield from path.glob(glob)
        path = path.parent

        

