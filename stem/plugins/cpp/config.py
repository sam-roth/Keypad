

from stem.core.nconfig import Settings, Field
from pathlib import Path

class CXXConfig(Settings):
    _ns_ = 'cxx'
    
    clang_library      = Field(Path)
    
    reparse_interval   = Field(float, 1.0)
    
    clang_flags        = Field(tuple, [], safe=True)
    clang_header_flags = Field(tuple, ['-x', 'c++-header'], safe=True)
    
    