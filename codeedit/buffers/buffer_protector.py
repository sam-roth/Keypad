
from .cursor import Cursor
from .span import Region, Span

class BufferProtector(object):
    def __init__(self, manip):
        self.manip = manip
        curs = Cursor(manip.buffer)
        self.region = None
        
        self.buffer = manip.buffer
        self.manip.will_execute_change.connect(self.__before_executing_change)
    
    def __before_executing_change(self, chg, intercept):
        if self.region is not None:
            if self.region.contains_inclusive(chg.inverse.pos)\
                    or self.region.contains_inclusive(chg.pos):
                # prevent change if it's in the protected region
                intercept()
