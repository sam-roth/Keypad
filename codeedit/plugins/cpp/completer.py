
from codeedit.core.tag import autoextend
from codeedit.control import BufferController
from codeedit.abstract.completion import AbstractCompletionView
from codeedit.api import interactive
from codeedit.core.responder import Responder
from codeedit.core import notification_center, AttributedString
from codeedit.control.interactive import dispatcher as interactive_dispatcher

from codeedit.buffers import Span, Cursor
from codeedit.plugins.semantics.completer import AbstractCompleter

import logging
import multiprocessing.dummy
import subprocess
import re
import textwrap

from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer


via_notification_center = notification_center.via_notification_center

def _as_posix_or_none(x):
    if x is None:
        return None
    else:
        return x.as_posix()


@interactive('lt')
def lt(responder: object):
    interactive_dispatcher.dispatch(responder, 'edit', '/Users/Sam/Desktop/clangserver/testproj/src/main.cc')
    interactive_dispatcher.dispatch(responder, 'tag', 'syntax', '"c++"')


@autoextend(BufferController,
            lambda tags: tags.get('syntax') == 'c++')
class CXXCompleter(AbstractCompleter):

    TriggerPattern = re.compile(r'\.$')
    WordChar       = re.compile(r'[\w\d]')

    def __init__(self, buf_ctl):
        super().__init__(buf_ctl)

        address_callback_handler = SimpleXMLRPCServer(('127.0.0.1', 0), allow_none=True)

        @via_notification_center
        def use_address(addr):
            logging.debug('semantic engine server responded at %r', addr)
            host, port = addr
            self.proxy = ServerProxy('http://{}:{}'.format(host, port))
            self.proxy.enroll_compilation_database(self.buf_ctl.path.parent.parent.as_posix())
            self.__doc = None
            address_callback_handler.shutdown()
            logging.debug('success: terminating address callback server')

        logging.debug('launching callback server')
        address_callback_handler.register_function(use_address, 'use_address')
        self.pool = multiprocessing.dummy.Pool(processes=1)
        self.pool.apply_async(address_callback_handler.serve_forever)
        logging.debug('launching semantic engine server')
        self.proc = subprocess.Popen([
            '/Users/Sam/Desktop/clangserver/run.sh',
            'http://{}:{}'.format(*address_callback_handler.server_address)
        ])


    @staticmethod
    def __convert_compl_results(completions):
        results = []
        doc = []
        for completion in completions:
            chunks = []
            doc_chunks = []
            for chunk in completion.get('chunks', []):
                if chunk.get('kind') == 'TypedText':
                    chunks.append(chunk.get('spelling', ''))
                
                doc_chunks.append(chunk.get('spelling', ''))

            doc_chunks.append('\n\n')

            if 'brief_comment' in completion:
                doc_chunks.append(str(completion['brief_comment']))
            results.append([' '.join(chunks)])
            doc.append(' '.join(doc_chunks))
        
        return results, doc

    def _request_completions(self):
        line, col = self._start_pos
        import pprint

        def worker():
            compls = self.proxy.completions(
                self.buf_ctl.path.as_posix(),
                line+1,
                col+1,
                [(self.buf_ctl.path.as_posix(), self.buf_ctl.buffer.text)]
            )

            return compls



        @via_notification_center
        def callback(compls):
            try:
                conv_compls, doc = self.__convert_compl_results(compls)
                self.__doc = doc
                self.show_completions(conv_compls)
            except:
                logging.exception('exception in c++ completion')

        self.pool.apply_async(worker, callback=callback)


    def _request_docs(self, index):
        if self.__doc is not None:
            self.show_documentation([self.__doc[index]])

