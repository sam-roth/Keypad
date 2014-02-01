
from clang import cindex
import logging
import pickle

from collections import namedtuple

class SemanticEngine(object):
    def __init__(self):
        self.index = cindex.Index.create()
        self.compilation_databases = []
        self.trans_units = {}

    def enroll_compilation_database(self, path):
        '''
        Add the JSON `CompilationDatabase` located in the directory `path` to 
        the list of compilation databases.
        '''
        dbase = cindex.CompilationDatabase.fromDirectory(path)
        self.compilation_databases.append(dbase)
    
        logging.info('Enrolled compilation database %r.', path)

    def compile_commands(self, filename):
        '''
        Find the first set of compile commands for the `filename` given.

        :rtype: clang.cindex.CompileCommand
        '''
        for cd in self.compilation_databases:
            commands = cd.getCompileCommands(filename)
            if commands is not None:
                for command in commands:
                    # return the first set of compile commands 
                    return command
        else:
            raise KeyError(filename)

    def clang_flags(self, filename):
        commands = self.compile_commands(filename)

        results = []
        for flag in commands.arguments:
            if flag == '-c':
                break
            results.append(flag)
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
            tu = self.index.parse(filename, 
                                  args=commands,
                                  options=cindex.TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION | 
                                  cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE)
            tu.reparse(unsaved_files)
            self.trans_units[filename] = tu
            return tu

    def reparse(self, path):
        tu = self.translation_unit(path)
        tu.reparse()
        logging.info('Reparsed translation unit %r.', path)

#    def completions(self, filename, line, col):
#        '''
#        :rtype: clang.cindex.CodeCompletionResults
#        '''
#        try:
#            tu = self.translation_unit(filename)
#            return tu.codeComplete(filename, line, col, include_brief_comments=True)
#            assert isinstance(results, cindex.CodeCompletionResults)
#
#            completions = []
#            
#            for result in results.results:
#                assert isinstance(result, cindex.CodeCompletionResult)
#                
#                completions.append(str(result.string))
#
#            return completions
#        except:
#            import traceback
#            traceback.print_exc()
#

    
            
        

SemanticEngine.instance = SemanticEngine()

    
