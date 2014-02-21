

from PyQt4.Qt import *

from stem.qt.view import TextViewSettings
from stem.qt import text_rendering as rendering
from stem.qt.qt_util import ending

from stem.api import interactive, BufferController


import copy
        
def render_buffer_to_printer(buff, printer, settings):
    '''
    Render a buffer to a QPrinter.

    :type buff: stem.buffers.Buffer
    :type printer: PyQt4.Qt.QPrinter
    :type settings: stem.qt.view.TextViewSettings
    '''
    

    painter = QPainter(printer)

    fm = QFontMetricsF(settings.q_font)
    page_width_chars = int(printer.pageRect(QPrinter.DevicePixel).width() / fm.width('x'))

    with ending(painter):

        y = 0

        for line_number, logical_line in enumerate(buff.lines):

            for line in logical_line.split_every(page_width_chars):
                size = rendering.text_size(line, settings, printer.pageRect(QPrinter.DevicePixel).width())
                #size.setWidth(printer.pageRect(QPrinter.DevicePixel).width())
                
                if y + size.height() >= printer.pageRect(QPrinter.DevicePixel).height():
                    printer.newPage()
                    y = 0

                rect = QRectF(QPointF(0, y), size)
                
                rendering.paint_attr_text(painter, line, rect, settings)

                y = rect.bottom()



@interactive('qprint')
def qt_print_buffer(buff: BufferController):
    printscale = buff.tags.get('printscale', 4)
    printer = QPrinter(QPrinter.HighResolution)
    dlg = QPrintDialog(printer, buff.view)

    if dlg.exec():
        settings = copy.copy(buff.view.settings)
        #settings.word_wrap = True
        settings.q_font = QFont(settings.q_font)
        settings.q_font.setPixelSize(int(settings.q_font.pointSize() * printscale))
        settings.q_font.setStyleStrategy(QFont.PreferAntialias)

        render_buffer_to_printer(buff.buffer, dlg.printer(), settings)


       
