
from stem.core import AttributedString
from stem.abstract.code import RelatedName, Diagnostic, AbstractCallTip
from clang import cindex
from .config import CXXConfig
import textwrap
import logging
import os
import re


ClangOptions = (cindex.TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION |
                                  cindex.TranslationUnit.PARSE_CACHE_COMPLETION_RESULTS |
                                  cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE)
ClangHeaderOptions = ClangOptions | cindex.TranslationUnit.PARSE_INCOMPLETE
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

def format_synopsis(syn):
    syn, _ = re.subn(r'\s+', ' ', syn)

    syn, _ = re.subn(r'''\s* ( [(){}\[\]<>] ) \s*''',
                     r'\1',
                     syn,
                     flags=re.VERBOSE)
    syn, _ = re.subn(r'\s*(\*|&)\s*(?=\w)', r' \1', syn)
    syn, _ = re.subn(r'\s*,\s*', ', ', syn)
    return syn

_kind_names = {
    'CXX_METHOD': AttributedString('method', lexcat='function'),
    'FUNCTION_DECL': AttributedString('function', lexcat='function'),
    'FUNCTION_TEMPLATE': AttributedString('function template', lexcat='function'),
    'DESTRUCTOR': AttributedString('destructor', lexcat='function'),
    'CONSTRUCTOR': AttributedString('constructor', lexcat='function'),
    'PARM_DECL': AttributedString('argument', lexcat='docstring'),
    'FIELD_DECL': AttributedString('field', lexcat='docstring'),
    'VAR_DECL': AttributedString('variable', lexcat='docstring'),
    'ENUM_CONSTANT_DECL': AttributedString('variable', lexcat='docstring'),
    'CLASS_DECL': AttributedString('class', lexcat='type'),
    'STRUCT_DECL': AttributedString('struct', lexcat='type'),
    'CLASS_TEMPLATE': AttributedString('class template', lexcat='type'),
    'TYPEDEF_DECL': AttributedString('typedef', lexcat='type'),
    'NAMESPACE': AttributedString('namespace', lexcat='preprocessor'),
    'MACRO_DEFINITION': AttributedString('macro', lexcat='preprocessor'),
    'NOT_IMPLEMENTED': AttributedString('not implemented', italic=True, lexcat='comment')
}

_empty = AttributedString()


def _might_be_header(filename):
    '''
    Determine if the filename conforms to known header extensions.
    '''
    
    _, ext = os.path.splitext(filename)
    
    return not ext or ext.lower() in (b'.h', b'.hpp', b'.hh')
    

class Engine:
    def __init__(self, config):
        assert isinstance(config, CXXConfig)
        self.config = config

        self.index = cindex.Index.create()
        self._translation_units = {}

    def completions(self, filename, pos, unsaved):
        tu = self.unit(filename, unsaved, reparse=False)

        line, col = pos

        cr = tu.codeComplete(
            str(filename).encode(), 
            line+1, col+1, 
            unsaved_files=self.encode_unsaved(unsaved),
        )
        
        self.last_completion_results = cr
        
        results = []
        
        for item in cr.results:
            results.append((AttributedString(self.typed_text(item.string)), 
                                             _kind_names.get(item.kind.name, _empty)))
        
        return results
    
    def completion_docs(self, index):
        cr = self.last_completion_results.results[index]
        assert isinstance(cr, cindex.CodeCompletionResult)
        
        synopsis = format_synopsis(' '.join(chunk.spelling for chunk in cr.string))
            
        
        lines = [AttributedString(synopsis)]
        comment = frombytes(cr.string.briefComment.spelling)
        if comment is not None:
            for line in textwrap.wrap(comment, 50): # FIXME: implement proper wrapping in the UI
                lines.append(AttributedString(line))
        
        return lines
        
    
    def unit(self, filename, unsaved, reparse=True):
        possibly_header = _might_be_header(filename)
        
        unsaved = self.encode_unsaved(unsaved)
        if filename not in self._translation_units:
            try:
                res = self.index.parse(
                    tobytes(str(filename)),
                    args=self.config.clang_header_flags if possibly_header else self.config.clang_flags,
                    unsaved_files=unsaved,
                    options=ClangHeaderOptions if possibly_header else ClangOptions
                )
                reparse = True
            except AssertionError:
                logging.exception('assertion failure in cindex')
                raise cindex.TranslationUnitLoadError
            else:
                self._translation_units[filename] = res
        else:
            res = self._translation_units[filename]

        if reparse:
            res.reparse(unsaved, options=ClangHeaderOptions if possibly_header else ClangOptions)    
        self.tu = res
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
        if getattr(worker, 'engine', None) is None and self.config.clang_library is not None:
            cindex.Config.set_library_file(str(self.config.clang_library))
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
    
    
        def suitable(c):
            return c is not None and c != curs and c.location is not None and c.location.file is not None
                
        if self.types & RelatedName.Type.decl:
            defn = curs.get_definition()
            if defn is None:
                decl = None
            else:
                decl = defn.canonical
                
                
#                 if suitable(decl):
#                     print('**found defn.canon:', decl.spelling, '**')
            
            if not suitable(decl):
                decl = curs.referenced_cursor
                
#                 if suitable(decl):
#                     print('**found rc:', decl.spelling, '**')
            if not suitable(decl):
                decl = curs.canonical
#                 if suitable(decl):
#                     print('**found canon:', decl, '**')
                    
            if not suitable(decl):
                dtype = curs.type
                if dtype is not None:
                    while dtype.kind == cindex.TypeKind.POINTER:
                        p = dtype.get_pointee()
                        if p is not None:
                            dtype = p
                        else:
                            break
                            
                    decl = dtype.get_declaration()
                    
            if suitable(decl):
                results.append(make_related_name(RelatedName.Type.decl, decl))

        #print('**results found', results, '**')
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
        
severity_map = {
    cindex.Diagnostic.Note: Diagnostic.Severity.note,
    cindex.Diagnostic.Warning: Diagnostic.Severity.warning,
    cindex.Diagnostic.Error: Diagnostic.Severity.error,
    cindex.Diagnostic.Fatal: Diagnostic.Severity.fatal
}

class CPPCallTip(AbstractCallTip):
    def __init__(self, tip):
        self.tip = tip
    
    def to_astring(self, n):
        return self.tip
        

class GetCallTipTask(AbstractCodeTask):
    def __init__(self, text, *args, **kw):
        super().__init__(*args, **kw)
        self.text = text
        
    def process(self, engine):
        assert isinstance(engine, Engine)
        
        engine.completions(self.filename, self.pos, self.unsaved_files)
        
        for compl in engine.last_completion_results.results:

#             print(compl)

            assert isinstance(compl, cindex.CodeCompletionResult)
            if engine.typed_text(compl.string) == self.text:
                syn = format_synopsis(' '.join(c.spelling for c in compl.string))
                return CPPCallTip(AttributedString(syn))
#             else:
#                 print('***no match:', engine.typed_text(compl.string)) #, self.text)
#         else:
#             print('nothing found')
#  
#         try:
#             tu = engine.unit(self.filename, self.unsaved_files)
#         except cindex.TranslationUnitLoadError:
#             return None
#         
#         y, x = self.pos
#         curs = cindex.Cursor.from_location(tu, 
#                                            tu.get_location(tobytes(self.filename), (y+1, x)))
#         
#         print(curs.referenced_cursor)
#         print(curs.kind.name)
#         print(curs.spelling)
#         print(curs.lexical_parent.spelling if curs.lexical_parent else None)
#         print(curs.semantic_parent.spelling if curs.semantic_parent else None)
#         
#         
#         
class GetDiagnosticsTask(AbstractCodeTask):
    def process(self, engine):
        assert isinstance(engine, Engine)
        
        try:
            tu = engine.unit(self.filename, self.unsaved_files)
        except cindex.TranslationUnitLoadError:
            return []
        
        results = []
        
        for diag in tu.diagnostics:
            assert isinstance(diag, cindex.Diagnostic)
            severity = severity_map.get(diag.severity, Diagnostic.Severity.unknown)
            loc = diag.location
            assert isinstance(loc, cindex.SourceLocation)
            ranges = []
            for r in diag.ranges:
                assert isinstance(r, cindex.SourceRange)
                if r.start.file is None:
                    fname = frombytes(loc.file.name)
                else:
                    fname = frombytes(r.start.file.name)
                start = r.start.line - 1, r.start.column - 1
                end = r.end.line - 1, r.end.column - 1
                
                if not any(x < 0 for x in start + end):
                    ranges.append((fname, start, end))
            if not ranges and loc.line > 0 and loc.column > 1:
                ranges.append((frombytes(loc.file.name),
                              (loc.line-1, loc.column-2),
                              (loc.line-1, loc.column-1)))
            
            results.append(
                Diagnostic(
                    severity,
                    frombytes(diag.spelling),
                    ranges,
                )
            )
        
        return results

