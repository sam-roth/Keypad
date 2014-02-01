

from clang import cindex
import logging
import pprint

class ServerMethods(object):
    def __init__(self):
        self._engine = None
        #self.engine = semantic_engine.SemanticEngine()
    
    def set_clang_path(self, path):
        cindex.Config.set_library_path(path)

    @property
    def engine(self):
        if self._engine is None:
            import semantic_engine
            self._engine = semantic_engine.SemanticEngine()
        return self._engine

    def enroll_compilation_database(self, path):
        self.engine.enroll_compilation_database(path)


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

            #logging.info('Chunk: %r', chunk_dict)

            chunk_dicts.append(chunk_dict)

        
        return dict(
            kind=completion.kind.name,
            chunks=chunk_dicts,
            availability=completion.string.availability.name,
            priority=completion.string.priority,
            brief_comment=completion.string.briefComment.spelling
        )

        
    def completions(self, filename, line, col, unsaved_files=[]):
        try:
            logging.info('processing request')
            tu = self.engine.translation_unit(filename, unsaved_files)
            #logging.info('reparsing translation unit')
            #tu.reparse(unsaved_files)
            
            #for name, contents in unsaved_files:
            #    print name
            #    print '='*80
            #    print contents

            #logging.info('Unsaved files: %s', pprint.pformat(unsaved_files))
            
            logging.info('finding code completions')
            completions = tu.codeComplete(filename, 
                                          line,
                                          col, 
                                          include_brief_comments=True,
                                          unsaved_files=unsaved_files)

            logging.info('retrieved completions')
            #logging.info('got completions %r', completions)

            assert isinstance(completions, cindex.CodeCompletionResults)

            return [self._convert_completion_result(r) for r in completions.results]
        except:
            import traceback
            traceback.print_exc()


