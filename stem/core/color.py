

from collections import namedtuple

import colorsys

class Color(namedtuple('Color', 'red green blue alpha')):
        
    @classmethod
    def _parse_hexstring(cls, hexstring):
        
        if not hexstring.startswith('#'):
            raise ValueError('hex color must begin with "#": {!r}'.format(hexstring))

        if len(hexstring) not in (4, 7):
            raise ValueError('hex color must be either three or six hex digits long.')

        num = int(hexstring[1:], 16)
        if len(hexstring) == 4:

            b = 0xF & num
            g = (0xF0 & num) >> 4
            r = (0xF00 & num) >> 8
            
            return b | (b << 4) | (g << 8) | (g << 12) | (r << 16) | (r << 20)

        elif len(hexstring) == 7:
            return num
        

    @classmethod
    def from_rgb(cls, red, green, blue, alpha=255):
        return cls(red, green, blue, alpha)
    
    @classmethod
    def from_hsv(cls, hue, sat, val, alpha=255):
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        return cls.from_rgb(r, g, b, alpha)

            
    @classmethod
    def from_hex(cls, num):
        if isinstance(num, Color):
            return num

        if isinstance(num, str):
            num = cls._parse_hexstring(num)
        
        b = (0x0000FF & num)
        g = (0x00FF00 & num) >> 8
        r = (0xFF0000 & num) >> 16
        
        return cls.from_rgb(r, g, b)


    @property
    def int(self):
        return ((self.red & 0xFF) << 16) | ((self.green & 0xFF) << 8) | (self.blue & 0xFF)

    @property
    def hex(self):
        return '#{:06x}'.format(self.int)

    @property
    def hsv(self):
        r,g,b,_ = self
        return colorsys.rgb_to_hsv(r,g,b)

    @property
    def value_inverse(self):
        h,s,v = self.hsv

        return self.from_hsv(h, s, 255-v, self.alpha)

    @property
    def css_rgba(self):
        return 'rgba({}, {}, {}, {}%)'.format(self.red, self.green, self.blue, self.alpha/255*100)
    
    
    def mean(self, other):
        return Color(*[int((x+y)/2) for (x,y) in zip(self, other)])
        
        
