

import pathlib
import glob
import logging
import os.path

def search_upwards(path, glob):
    if path is not None:
        path = pathlib.Path(path)
        while path is not None:
            results = list(path.glob(glob))
            
            yield from results
            if path.parent == path:
                break
            else:
                path = path.parent

        
def same_file(path1, path2):
    path1 = pathlib.Path(path1)
    path2 = pathlib.Path(path2)
    return os.path.samefile(str(path1.resolve()), str(path2.resolve()))