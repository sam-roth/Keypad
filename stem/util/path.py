

import pathlib
import glob
import logging

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

        

