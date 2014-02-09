

import pathlib
import glob


def search_upwards(path, glob):
    if path is not None:
        path = pathlib.Path(path)
        while path is not None and path.parent != path:
            yield from path.glob(glob)
            path = path.parent

        

