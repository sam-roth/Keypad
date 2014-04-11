
from stem.core import filetype

def make_cxx_code_model(*args):
    from .cppmodel import CXXCodeModel
    return CXXCodeModel(*args)
    
filetype.Filetype('c++', 
                  suffixes='.c .cc .C .cpp .c++ .cxx .h .hh .H .hpp .h++ .hxx'.split(),
                  tags={'parmatch': True, 'commentchar': '//'},
                  code_model=make_cxx_code_model)
                