
from collections import namedtuple


from stem.api import autoextend, interactive, BufferController
from stem.buffers import Cursor, Span


@autoextend(BufferController, lambda tags: tags.get('template'))
class TemplateController(object):
    def __init__(self, bufctl):
        '''
        Creates template fields that are substituted by the user.

        :type bufctl: stem.api.BufferController
        '''
        self.bufctl = bufctl
        self.spans = []
        self.bufctl.add_tags(template_controller=self)
        self.text_view_settings = self.bufctl.view.settings
        self.bufctl.canonical_cursor.modifiers.append(self.__slot_modifier)
        self.bufctl.buffer_was_changed.connect(self.__on_buffer_text_modified)

    def __slot_modifier(self, curs, pos):
        '''
        makes cursor skip over slots
        '''
        remove_spans = []
        for span in self.spans:
            if span.start_curs.pos >= span.end_curs.pos:
                remove_spans.append(span)
                continue

            if span.contains_inclusive(pos): #and self.bufctl.anchor_cursor is None:
                if pos > curs.pos:
                    return span.end_curs.pos
                else:
                    return span.start_curs.pos

        return pos

    def __on_buffer_text_modified(self, chg):
        '''
        hook for removing defunct slots
        '''
        remove_spans = []

        for span in self.spans:
            if span.start_curs.pos >= span.end_curs.pos:
                remove_spans.append(span)

        for span in remove_spans:
            self.spans.remove(span)

        if remove_spans:
            self._update_overlays()


    def add_slot(self, span):
        self.spans.append(span)
        self._update_overlays()

    def _update_overlays(self):
        self.bufctl.view.overlay_spans[id(self)] = tuple(
            (s, 'cartouche', self.text_view_settings.fgcolor)
            for s in self.spans
        )
        self.bufctl.refresh_view()


@interactive('addslot')
def addslot(bctl: BufferController, text):
    try:
        tctl = bctl.tags['template_controller']
    except KeyError:
        bctl.add_tags(template=True)
        tctl = bctl.tags['template_controller']

    
    curs = bctl.canonical_cursor

    start_pos = curs.pos
    with bctl.history.transaction():
        curs.insert(text)
    

    end_curs = Cursor(bctl.buffer).move(*curs.pos)
    end_curs.chirality = Cursor.Chirality.Left

    span = Span(
        Cursor(bctl.buffer).move(*start_pos),
        end_curs
    )

    tctl.add_slot(span)

