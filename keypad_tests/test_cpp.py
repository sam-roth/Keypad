'''
Test the C++ code model.


If these tests fail on your machine, you may need to add a test_keypadrc on your PYTHONPATH
with the appropriate configuration. Here's what mine looks like::

    from keypad.api import Config
    from keypad.plugins.cpp.config import CXXConfig
    cxxsettings = CXXConfig.from_config(Config.root)
    cxxsettings.clang_library = '/Library/Developer/CommandLineTools/usr/lib/libclang.dylib'
    
'''



import pathlib, sys

from keypad.plugins import cpp

thisfile = pathlib.Path(cpp.__file__).absolute()
sys.path.insert(0, str(thisfile.parent.parent.parent.parent / 'third-party'))

try:
    import test_keypadrc
except ImportError:
    pass

import unittest

from keypad.plugins.cpp.cppmodel import CXXCodeModel, CXXCompletionResults
from keypad.plugins.cpp.config import CXXConfig
from keypad.core.nconfig import Config
from keypad.buffers import Buffer, Cursor, Span
from keypad.abstract.code import RelatedName, Diagnostic
import pprint

import sys



def add_to_buffer(buff, text):
    result = []
    for part in text.split('%%'):
        buff.insert(buff.end_pos, part)
        result.append(buff.end_pos)
    result.pop()
    return result
    

class TestCXXCodeModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buffer = Buffer()
        cls.cmodel = CXXCodeModel(cls.buffer, Config.root)
        cls.cmodel.path = '/tmp/test.cpp'

    @classmethod
    def tearDownClass(cls):
        cls.cmodel.dispose()

    def setUp(self):
        self.buffer.remove((0,0), len(self.buffer.text))

        
    def test_completion(self):
        self.buffer.insert(
            (0, 0),
            'struct S { int abcdef; };\n'
            'void foo() { S s; s.' 
        )
        ep = self.buffer.end_pos
        self.buffer.insert(ep, 
            '   }\n')
        f = self.cmodel.completions_async(ep)
        
        res = f.result()
        
        assert isinstance(res, CXXCompletionResults)
        
        
        for i, row in enumerate(res.rows):
            if 'abcdef' == res.text(i):
                break
        else:
            self.fail('Expected abcdef when completing on s')
        
        
    def test_find_decl(self):
        
        decl_pos, find_decl_pos = add_to_buffer(
            self.buffer,
            '''
            void %%foo();
            
            void foo() { }
            
            void bar()
            {
                foo%%();
            }
            '''
        )

        f = self.cmodel.find_related_async(find_decl_pos, self.cmodel.RelatedNameType.decl)
        
        res = f.result(timeout=5)
        
        assert len(res) == 1
        result = res[0]
        
        assert isinstance(result, RelatedName)
        assert result.pos == decl_pos
        

    def test_find_defn(self):
        
        defn_pos, find_defn_pos = add_to_buffer(
            self.buffer,
            '''
            void foo();
            
            void %%foo() { }
            
            void bar()
            {
                foo%%();
            }
            '''
        )
        
        
        f = self.cmodel.find_related_async(find_defn_pos, self.cmodel.RelatedNameType.defn)
        
        res = f.result(timeout=5)
        
        assert len(res) == 1
        result = res[0]
        
        assert isinstance(result, RelatedName)
        assert result.pos == defn_pos
        
        
    def test_get_diagnostics(self):
        
        missing_semicolon_pos, = add_to_buffer(
            self.buffer,
            '''
            void bar();
            
            void foo()
            {
                bar()%%
            }
            '''
        )
        
        assert self.cmodel.can_provide_diagnostics
        
        diags = self.cmodel.diagnostics_async().result()
        assert len(diags) == 1
        diag = diags[0]
        
        assert isinstance(diag, Diagnostic)
        assert len(diag.ranges) == 1
        assert diag.ranges[0][2] == missing_semicolon_pos