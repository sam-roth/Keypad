

from stem.core.nconfig import ConfigGroup, Field
from pathlib import Path

class CXXConfig(ConfigGroup):
    _ns_ = 'cxx'
    
    clang_library      = Field(Path)
    
    reparse_interval   = Field(float, 1.0)
    
    clang_flags        = Field(list, [])
    clang_header_flags = Field(list, ['-x', 'c++-header'])                       