

from collections import namedtuple

import colorsys
import math


# CIE L*a*b* Color conversion functions from http://davidad.net/colorviz/ .

def _finv(t):
    if t>(6.0/29.0):
        return t*t*t
    else:
        return 3*(6.0/29.0)*(6.0/29.0)*(t-4.0/29.0)
        
def _lab2xyz(l, a, b):
    sl = (l + 0.16) / 1.16
    
    x = 0.9643 * _finv(sl + (a/5.0))
    y = 1.00   * _finv(sl)
    z = 0.8251 * _finv(sl - (b/2.0))

    return x, y, z


def _clamp(x, lo, hi):
    if x < lo:
        return lo
    elif x > hi:
        return hi
    else:
        return x

def _correct(cl):
    a = 0.055
    return (12.92 * cl 
            if cl <= 0.0031308
            else (1 + a) * cl ** (1/2.4) - a)


def _rgb_comp_to_xyz(r):
    # based on https://github.com/gka/chroma.js/blob/master/chroma.js
    r /= 255
    if r <= 0.04045:
        return r / 12.92
    else:
        return ((r + 0.055) / 1.055) ** 2.4

def _xyz_comp_to_lab(x):
    if x > 0.008856:
        return x ** (1/3)
    else:
        return 7.787037 * x + 4/29

def _rgb2lab(r, g, b):

    X = 0.950470
    Y = 1
    Z = 1.088830

    r, g, b = map(_rgb_comp_to_xyz, (r, g, b))

    x = _xyz_comp_to_lab((0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / X)
    y = _xyz_comp_to_lab((0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / Y)
    z = _xyz_comp_to_lab((0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / Z)

    l = 116 * y - 16
    a = 500 * (x - y)
    b = 200 * (y - z)

    return l, a, b

def _xyz2rgb(x, y, z):

    rl =  3.2406*x - 1.5372*y - 0.4986*z
    gl = -0.9689*x + 1.8758*y + 0.0415*z
    bl =  0.0557*x - 0.2040*y + 1.0570*z

    rl = _clamp(rl, 0, 1)
    gl = _clamp(gl, 0, 1)
    bl = _clamp(bl, 0, 1)

    r = int(255 * _correct(rl))
    g = int(255 * _correct(gl))
    b = int(255 * _correct(bl))

    return r, g, b

def _lab2rgb(l, a, b):
    x, y, z = _lab2xyz(l, a, b)
    return _xyz2rgb(x, y, z)

def _cl2rgb(c, l):
    lab_l = l * 0.61 + 0.09
    angle = math.pi / 3 - 2 * math.pi * c
    r = l * 0.311 + 0.125
    a = math.sin(angle) * r
    b = math.cos(angle) * r

    return _lab2rgb(lab_l, a, b)

def _lch2lab(l, c, h):
    h *= math.pi / 180

    a = c * math.cos(h)
    b = c * math.sin(h)

    return l, a, b

def _lab2lch(l, a, b):
    c = (a * a + b * b) ** 0.5
    h = math.atan2(b, a) * 180 / math.pi

    return l, c, h




class Color(namedtuple('Color', 'red green blue alpha')):
    
    def __new__(cls, *args, **kw):
        total = len(args) + len(kw)

        if total == 4:
            return super().__new__(cls, *args, **kw)
        elif len(args) == 1 and len(kw) == 0:
            return cls.from_hex(args[0])
        else:
            raise TypeError('wrong number of arguments to Color constructor')

    @property
    def lab(self):
        r, g, b, _ = self
        l, a, b = _rgb2lab(r, g, b)
        return l/100, a/100, b/100

    @property
    def lch(self):
        l, a, b = self.lab
        l *= 100
        a *= 100
        b *= 100

        l, c, h = _lab2lch(l, a, b)
        return l / 100, c / 100, h



    @classmethod
    def _parse_hexstring(cls, hexstring):
        
        if not hexstring.startswith('#'):
            raise ValueError('hex color must begin with "#": {!r}'.format(hexstring))

        if len(hexstring) not in (4, 7, 9):
            raise ValueError('hex color must be either three, six, or eight hex digits long.')

        num = int(hexstring[1:], 16)
        if len(hexstring) == 4:

            b = 0xF & num
            g = (0xF0 & num) >> 4
            r = (0xF00 & num) >> 8
            
            return b | (b << 4) | (g << 8) | (g << 12) | (r << 16) | (r << 20), 255

        elif len(hexstring) == 7:
            return num, 255
        elif len(hexstring) == 9:
            return num >> 8, num & 0xFF


    def brighter(self, value):
        '''
        Returns a color with a HSV value adjusted by the factor given.
        '''
        h,s,v = self.hsv
        v *= value
        return self.from_hsv(h,s,v,self.alpha)
        
    def lighter(self, value):
        '''
        Returns a color with an (L*, a*, b*) L* value adjusted by the factor given.
        '''
        l, a, b = self.lab
        return self.from_lab(_clamp(l * value, 0, 1), a, b)
        

    @classmethod
    def from_rgb(cls, red, green, blue, alpha=255):
        return cls(min(red, 255), min(green, 255), min(blue, 255), min(alpha, 255))
    
    @classmethod
    def from_hsv(cls, hue, sat, val, alpha=255):
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        return cls.from_rgb(r, g, b, alpha)

            
    @classmethod
    def from_hex(cls, num):
        alpha = 255
        if isinstance(num, Color):
            return num

        if isinstance(num, str):
            num, alpha = cls._parse_hexstring(num)
        
        b = (0x0000FF & num)
        g = (0x00FF00 & num) >> 8
        r = (0xFF0000 & num) >> 16
        
        return cls.from_rgb(r, g, b, alpha)
        
    @classmethod
    def from_cl(cls, c, l, alpha=255):
        r, g, b = _cl2rgb(c, l)
        return cls(r, g, b, alpha)

    @classmethod
    def from_lab(cls, l, a, b, alpha=255):
        '''
        Return a new color converted from the CIE 1976 (L*, a*, b*) color space.

        The `l` parameter controls lightness and is on the real interval [0, 1].
        The `a` and `b` parameters control chromaticity (green-magenta and blue-
        yellow, respectively) and are on the real interval [-1, 1].
        '''
        r, g, b = _lab2rgb(l, a, b)
        return cls(r, g, b, alpha)

    @classmethod
    def from_lch(cls, l, c, h, alpha=255):
        '''
        Polar version of CIE 1976 (L*, a*, b*).
        
        .. math::
            l &\in [0, 1]\\
            c &\in [0, 1]\\
            h &\in [0, 360]

        '''
        l, a, b = _lch2lab(l, c, h)
        return cls.from_lab(l, a, b, alpha)

    def composite(self, other):
        lr,lg,lb,la = self
        rr,rg,rb,ra = other

        la /= 255
        ra /= 255

        ra *= (1 - la) # the background is filtered through the foreground

        return Color.from_rgb(int(lr * la + rr * ra),
                              int(lg * la + rg * ra),
                              int(lb * la + rb * ra),
                              int(255 * (la + ra)))
        



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


        
        
