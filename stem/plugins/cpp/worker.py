import os, signal, contextlib
import os.path

@contextlib.contextmanager
def acquiring_without_blocking(lock):
    acquired = False
    try:
        acquired = lock.acquire(False)
        if not acquired:
            raise threading.ThreadError('lock is locked')
        yield
    finally:
        if acquired:
            lock.release()


import multiprocessing
from multiprocessing.managers import BaseManager

import logging
from clang import cindex

from . import options
import threading


def encode(s):
    if isinstance(s, bytes):
        return s
    else:
        return str(s).encode()

def decode_recursively(s):
    if isinstance(s, bytes):
        return s.decode()
    elif isinstance(s, list):
        return [decode_recursively(x) for x in s]
    elif isinstance(s, dict):
        return {decode_recursively(k): decode_recursively(v) for (k, v) in s.items()}
    else:
        return s
ParseOptions = (cindex.TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION |
                                  cindex.TranslationUnit.PARSE_INCOMPLETE | 
                                  cindex.TranslationUnit.PARSE_CACHE_COMPLETION_RESULTS |
                                  cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE)

def might_be_header(filename):
    '''
    Determine if the filename conforms to known header extensions.
    '''
    
    _, ext = os.path.splitext(filename)
    
    return ext.lower() in (b'.h', b'.hpp', b'.hh')

    

class WorkerSemanticEngine(object):
    def __init__(self):
        cindex.conf.get_cindex_library().clang_toggleCrashRecovery(1)
        self.index = cindex.Index.create()
        self.compilation_databases = []
        self.trans_units = {}

    def enroll_compilation_database(self, path):
        '''
        Add the JSON `CompilationDatabase` located in the directory `path` to 
        the list of compilation databases.
        '''
        dbase = cindex.CompilationDatabase.fromDirectory(encode(path))
        self.compilation_databases.append(dbase)
    
        logging.info('Enrolled compilation database %r.', path)

    def compile_commands(self, filename):
        '''
        Find the first set of compile commands for the `filename` given.

        :rtype: clang.cindex.CompileCommand
        '''
        for cd in self.compilation_databases:
            commands = cd.getCompileCommands(os.path.abspath(filename))
            if commands is not None:
                for command in commands:
                    # return the first set of compile commands 
                    return command
        else:
            raise KeyError(filename)

    def clang_flags(self, filename):
        try:
            commands = self.compile_commands(filename)
        except KeyError:
            if might_be_header(filename):
                default_flags = 'DefaultClangHeaderFlags'
            else:
                default_flags = 'DefaultClangFlags'
            logging.debug('used default flags for %r (%r)', filename, default_flags)
            return list(map(encode, getattr(options, default_flags, [])))
        else:

            results = []
            for flag in commands.arguments:
                if flag == b'-c':
                    break
                results.append(flag)
            logging.debug('used flags from cdb for %r: %r', filename, results)
            return results



    def translation_unit(self, filename, unsaved_files=[]):
        '''
        Find the `TranslationUnit` representing the `filename` given.

        :rtype: clang.cindex.TranslationUnit
        '''
        tu = self.trans_units.get(filename)
        if tu is not None:
            assert isinstance(tu, cindex.TranslationUnit)
            return tu
        else:
            commands = self.clang_flags(filename)
            tu = self.index.parse(encode(filename),
                                  args=commands,
                                  options=ParseOptions)
            tu.reparse(unsaved_files)
            self.trans_units[filename] = tu
            return tu

    def reparse(self, path):
        tu = self.translation_unit(path)
        tu.reparse()
        logging.info('Reparsed translation unit %r.', path)

class SemanticEngine(object):

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()


    @property
    def engine(self):
        if self._engine is None:
            if options.ClangLibrary is not None:
                cindex.Config.set_library_file(str(options.ClangLibrary))
            self._engine = WorkerSemanticEngine()
        return self._engine

    def enroll_compilation_database(self, path):
        self._engine.enroll_compilation_database(path)


    def _convert_completion_result(self, completion):
        '''
        :type completion: clang.cindex.CodeCompletionResult
        '''
        
        chunk_dicts = []
        for chunk in completion.string:
            assert isinstance(chunk, cindex.CompletionChunk)
            
            chunk_dict = dict(
                kind=chunk.kind.name,
                spelling=chunk.spelling
            )


            chunk_dicts.append(chunk_dict)

        
        return decode_recursively(dict(
            kind=completion.kind.name,
            chunks=chunk_dicts,
            availability=completion.string.availability.name,
            priority=completion.string.priority,
            brief_comment=completion.string.briefComment.spelling
        ))

    @staticmethod
    def _convert_location(loc):
        if loc is not None:
            return (loc.file.name if loc.file is not None else '<unknown>', (loc.line, loc.column))
        else:
            return ('<unknown>', (0, 0))
    
    @staticmethod
    def _convert_diagnostic(diag):
        return decode_recursively(dict(
            severity=diag.severity,
            location=SemanticEngine._convert_location(diag.location),
            spelling=diag.spelling
        ))
    @staticmethod
    def _cvt_unsaved(unsaved_files):
        return [(f.encode(), c.encode()) for (f,c) in unsaved_files]


    def check_living(self): 
        pass

    def reparse_and_get_diagnostics(self, filename, unsaved_files=[]):
        try:
            with acquiring_without_blocking(self._lock):
                unsaved_files = self._cvt_unsaved(unsaved_files)
                tu = self.engine.translation_unit(encode(filename), unsaved_files)
                tu.reparse(unsaved_files=unsaved_files, options=ParseOptions)

                diags = [self._convert_diagnostic(diag) for diag in tu.diagnostics]
                return diags

        except threading.ThreadError:
            return []


    def completions(self, filename, line, col, unsaved_files=[]):
        with self._lock:
            unsaved_files = self._cvt_unsaved(unsaved_files)
            tu = self.engine.translation_unit(encode(filename), unsaved_files)
            
            completions = tu.codeComplete(encode(filename), 
                                          line,
                                          col, 
                                          include_brief_comments=True,
                                          unsaved_files=unsaved_files)

            assert isinstance(completions, cindex.CodeCompletionResults)
            compls = [self._convert_completion_result(r) for r in completions.results]

            return compls


    def find_definition(self, filename, line, col, unsaved_files=[]):
        with self._lock:
            unsaved_files = self._cvt_unsaved(unsaved_files)
            tu = self.engine.translation_unit(encode(filename), unsaved_files)
            
            curs = cindex.Cursor.from_location(tu,
                                               tu.get_location(encode(filename),
                                                               (line, col)))
            defn = curs.get_definition()
            loc = defn.location
            return (decode_recursively(loc.file.name), loc.line, loc.column)
        
        

class WorkerManager(BaseManager):
    pass


WorkerManager.register('SemanticEngine', SemanticEngine)


