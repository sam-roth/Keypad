

import unittest
import pathlib
# from .pymodel import PythonCodeModel, PythonCompletionResults, RelatedName

from .cppmodel import CXXCodeModel, CXXCompletionResults
from .config import CXXConfig
from stem.core.nconfig import Config
from stem.buffers import Buffer, Cursor, Span
from stem.abstract.code import RelatedName
import pprint


cxx_config = CXXConfig.from_config(Config.root)
cxx_config.clang_library = '/Library/Developer/CommandLineTools/usr/lib/libclang.dylib'

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
        
#         
#     def test_completion_docstring(self):
#         self.buffer.insert(
#             (0,0),
#             'def foo():\n'
#             '  "bar"\n'
#             'foo'
#         )
#         
#         pos = self.buffer.end_pos
#         
#         f = self.cmodel.completions_async(pos)
#         
#         res = f.result(timeout=5)
#         
#         for i, row in enumerate(res.rows):
#             if row and row[0].text == 'foo':
#                 doc = res.doc_async(i).result(5)
#                 assert len(doc) == 3
#                 assert doc[2].text == 'bar'
#                 break
#         else:
#             self.fail('Expected that "foo" should be available as a completion result.')
#                 
        
        
    def test_find_decl(self):
        
        self.buffer.insert(
            (0,0),
            'struct S { int i; };\n'
        )
        pos = self.buffer.end_pos
        
        self.buffer.insert(
            pos,
            'S abcd;\n'
            'void foo() { abcd'
        )
        
        f = self.cmodel.find_related_async(self.buffer.end_pos, self.cmodel.RelatedNameType.decl)
        
        res = f.result(timeout=5)
        
        assert len(res) == 2
        result = res[0]
        
        print(res)
        assert isinstance(result, RelatedName)
        assert result.pos[0] == 1
        assert res[1].pos[0] == 2

    