

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
    if path1 is None or path2 is None:
        res = path1 is path2
    else:    
        try:
            path1 = pathlib.Path(path1)
            path2 = pathlib.Path(path2)
            res = os.path.samefile(str(path1.resolve()), str(path2.resolve()))
        except FileNotFoundError:
            res = os.path.normpath(str(path1.absolute())) == os.path.normpath(str(path2.absolute()))
    return res
    
    