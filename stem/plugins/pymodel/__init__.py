
from stem.core import filetype

def make_python_code_model(*args):
    from .pymodel import PythonCodeModel
    return PythonCodeModel(*args)

filetype.Filetype('python', suffixes=('.py',), tags={'parmatch': True}, code_model=make_python_code_model)

