
from stem.core import AttributedString
from stem.abstract.code import RelatedName
from clang import cindex
from .config import CXXConfig
import textwrap
ClangOptions = (cindex.TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION |
                                  cindex.TranslationUnit.PARSE_INCOMPLETE | 
                                  cindex.TranslationUnit.PARSE_CACHE_COMPLETION_RESULTS |
                                  cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE)

def expect(v, ty):
    if not isinstance(v, ty):
        try:
            tyname = ' or '.join(t.__name__ for t in ty)
        except TypeError:
            tyname = t.__name__
        
        raise TypeError('Expected {} not {}'.format(tyname, type(v).__name__))
            

def tobytes(s):
    if s is None:
        return None
        
    expect(s, (bytes, str))
    
    if isinstance(s, str):
        return s.encode()
    else:
        return s
        
def frombytes(s):
    if s is None:
        return None
        
    expect(s, (bytes, str))
    
    if isinstance(s, bytes):
        return s.decode()
    else:
        return s

class Engine:
    def __init__(self, config):
        assert isinstance(config, CXXConfig)
        self.config = config
        if config.clang_library is not None:
            cindex.Config.set_library_file(str(config.clang_library))
        self.index = cindex.Index.create()

    def completions(self, filename, pos, unsaved):
        tu = self.unit(filename, unsaved)

        line, col = pos

        cr = tu.codeComplete(
            str(filename).encode(), 
            line+1, col+1, 
            unsaved_files=self.encode_unsaved(unsaved),
        )
        
        self.last_completion_results = cr
        
        results = []
        
        for item in cr.results:
            results.append((AttributedString(self.typed_text(item.string)), ))
        
        return results
    
    def completion_docs(self, index):
        cr = self.last_completion_results.results[index]
        assert isinstance(cr, cindex.CodeCompletionResult)
        
        lines = []
        comment = frombytes(cr.string.briefComment.spelling)
        if comment is not None:
            for line in textwrap.wrap(comment, 35):
                lines.append(AttributedString(line))
        
        return lines
        
    
    def unit(self, filename, unsaved):
        unsaved = self.encode_unsaved(unsaved)
        res = self.index.parse(
            tobytes(str(filename)),
            args=[],
            unsaved_files=unsaved,
            options=ClangOptions
        )
        res.reparse(unsaved, options=ClangOptions)    
        
        return res
        
    @staticmethod
    def typed_text(cstring):
        '''
        Get only the typed text portion of a completion string.
        '''
        
        assert isinstance(cstring, cindex.CompletionString)
        
        def gen():
            for chunk in cstring:
                if chunk.isKindTypedText():
                    yield frombytes(chunk.spelling)
        return ' '.join(gen())
    
    @staticmethod
    def decode_completion_string(cstring):
        '''
        Convert a completion string to an AttributedString.
        
        '''
        assert isinstance(cstring, cindex.CompletionString)
        
        def gen():
            for chunk in cstring:                
                yield AttributedString(frombytes(chunk.spelling), 
                                        kind=chunk.kind.name)
        return AttributedString.join(' ', gen())
            
                
        

    @staticmethod
    def encode_unsaved(unsaved):
        return [(tobytes(str(k)), tobytes(v)) for (k, v) in unsaved]


class InitWorkerTask(object):
    def __init__(self, config):
        self.config = config

    def __call__(self, worker):
        worker.engine = Engine(self.config)

class AbstractCodeTask(object):
    def __init__(self, filename, pos, unsaved_files=[]):
        self.filename = str(filename)
        self.unsaved_files = unsaved_files
        self.pos = pos

    def process(self, engine):
        raise NotImplementedError

    def __call__(self, worker):
        engine = worker.engine
        return self.process(engine)



def make_related_name(ty, c):
    loc = c.location
    return RelatedName(
        ty,
        frombytes(loc.file.name),
        (loc.line-1, loc.column-1),
        frombytes(c.spelling)
    )
    
class FindRelatedTask(AbstractCodeTask):
    def __init__(self, types, *args, **kw):
        super().__init__(*args, **kw)
        self.types = types
    def process(self, engine):
        assert isinstance(engine, Engine)
        tu = engine.unit(self.filename, self.unsaved_files)
        enc_filename = tobytes(str(self.filename))
        line, col = self.pos
        
        curs = cindex.Cursor.from_location(
            tu,
            tu.get_location(
                enc_filename,
                (line+1, col)
            )
        )
        
        if curs is None:
            return []
            
        
        results = []
        
        if self.types & RelatedName.Type.defn:
            defn = curs.get_definition()
            if defn is not None:
                results.append(make_related_name(RelatedName.Type.defn, defn))
    
        if self.types & RelatedName.Type.decl:
            decl = curs.canonical
            if decl is not None:
                results.append(make_related_name(RelatedName.Type.decl, decl))
        
        import pprint
        pprint.pprint(results)
        return results

class CompletionTask(AbstractCodeTask):
    def process(self, engine):
        assert isinstance(engine, Engine)
        return engine.completions(self.filename, self.pos, self.unsaved_files)
        
class GetDocsTask(object):
    def __init__(self, index):
        self.index = index
    def __call__(self, worker):
        engine = worker.engine
        assert isinstance(engine, Engine)
        return engine.completion_docs(self.index)