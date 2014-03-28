

import unittest
from .pymodel import PythonCodeModel, PythonCompletionResults, RelatedName
from stem.core.conftree import ConfTree
from stem.buffers import Buffer, Cursor, Span


class TestPythonCodeModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = ConfTree()
        cls.buffer = Buffer()
        cls.cmodel = PythonCodeModel(cls.buffer, cls.config)
        cls.cmodel.path = '/tmp/test.py'
        
    @classmethod
    def tearDownClass(cls):
        cls.cmodel.dispose()
        
    def setUp(self):
        self.buffer.remove((0,0), len(self.buffer.text))

        
    def test_completion(self):
        self.buffer.insert(
            (0, 0),
            'import sys\n'
            'sys.'
        )
            
        f = self.cmodel.completions_async(self.buffer.end_pos)
        
        res = f.result(timeout=5)
        
        assert isinstance(res, PythonCompletionResults)
        
        for row in res.rows:
            if row:
                if row[0].text == 'argv':
                    break
        else:
            self.fail('Expected argv when completing on sys')
        
        
    def test_completion_docstring(self):
        self.buffer.insert(
            (0,0),
            'def foo():\n'
            '  "bar"\n'
            'foo'
        )
        
        pos = self.buffer.end_pos
        
        f = self.cmodel.completions_async(pos)
        
        res = f.result(timeout=5)
        
        for i, row in enumerate(res.rows):
            if row and row[0].text == 'foo':
                doc = res.doc_async(i).result(5)
                assert len(doc) == 3
                assert doc[2].text == 'bar'
                break
        else:
            self.fail('Expected that "foo" should be available as a completion result.')
                
        
        
    def test_find_decl(self):
        
        self.buffer.insert(
            (0,0),
            'class Foo: pass\n'
            'F'
        )
        pos = self.buffer.end_pos
        
        self.buffer.insert(
            pos,
            'oo\n'
        )
        
        f = self.cmodel.find_related_async(pos, self.cmodel.RelatedNameType.decl)
        
        res = f.result(timeout=5)
        
        assert len(res) == 1
        result = res[0]
        
        print(result)
        assert isinstance(result, RelatedName)
        assert result.pos[0] == 0
        

    