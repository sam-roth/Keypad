
import collections.abc

class Modifiers:
    Shift = 0x02000000
    Ctrl  = 0x04000000
    Alt   = 0x08000000
    Meta  = 0x10000000

    All   = Shift | Ctrl | Alt | Meta
    
    values = {
        'Shift': Shift,
        'Ctrl': Ctrl,
        'Alt': Alt,
        'Meta': Meta
    }

    conventionally_ordered_values = (
        ('Ctrl', Ctrl),
        ('Alt', Alt),
        ('Meta', Meta),
        ('Shift', Shift),
    )

class SimpleKeySequence(object):
    def __init__(self, modifiers, keycode, optional_modifiers=0):
        self._modifiers = int(modifiers) & Modifiers.All
        self._keycode = keycode
        self._optional_modifiers = optional_modifiers


    @property
    def modifiers(self): return self._modifiers

    @property
    def keycode(self): return self._keycode

    @property
    def optional_modifiers(self): return self._optional_modifiers

    def optional(self, modifiers):
        if isinstance(modifiers, KeySequenceBuilder):
            modifiers = modifiers._modifiers

        return SimpleKeySequence(self.modifiers, 
                                 self.keycode, 
                                 self.optional_modifiers | modifiers)

    @classmethod
    def _generate_modifier_names(cls, modifiers):
        for name, modifier in Modifiers.conventionally_ordered_values:
            if modifiers & modifier:
                yield name


    def __str__(self):
        def gen():
            global _key_names
            yield from self._generate_modifier_names(self.modifiers)
            yield _key_names.get(self.keycode, '<?>').capitalize()

        return '+'.join(gen())

    def __repr__(self):
        return str(self)

    def matches(self, other):
        if other.keycode != self.keycode:
            return False
        relevant_modifiers = self.modifiers & ~self.optional_modifiers
        other_relevant_modifiers = other.modifiers & ~self.optional_modifiers
        return relevant_modifiers == other_relevant_modifiers

import collections

_raise_exception = object() # default for KeySequenceDict.find

class KeySequenceDict(collections.abc.MutableMapping):
    '''
    Dictionary providing approximate matches for keys of type SimpleKeySequence.

    Simple Example:
    >>> k = KeySequenceDict(
    ...     (key.left.optional(shift), 'left'),
    ...     (key.right, 'right')
    ... )
    >>> k[key.left]
    'left'
    >>> k[key.right]
    'right'
    >>> k[shift.left]
    'left'
    >>> k[shift.right]
    Traceback (most recent call last):
      File "<ipython-input-26-69e4e4544a54>", line 1, in <module>
        k[shift.right]
      File "./codeedit/key.py", line 101, in __getitem__
        _, result = self.find(key)
      File "./codeedit/key.py", line 96, in find
        raise KeyError(key)
    KeyError: Shift+Right


    More thorough example:
    >>> d = KeySequenceDict(
    ...     (key.left.optional(shift), 'left'),
    ...     (key.right.optional(shift), 'right'),
    ...     (key.up, 'up'),
    ...     (ctrl.alt.delete.optional(shift.meta), 'restart'),
    ... )
    >>>
    >>> lookups = [
    ...     key.left,
    ...     shift.left,
    ...     key.right,
    ...     shift.right,
    ...     key.up,
    ...     shift.up,
    ...     ctrl.alt.delete,
    ...     ctrl.alt.shift.delete,
    ...     ctrl.alt.meta.delete,
    ...     ctrl.delete,
    ...     ctrl.alt.shift.meta.delete
    ... ]
    >>>
    >>> for lookup in lookups:
    ...         print('{:>40} => {}'.format(lookup, d.get(lookup)))
                                        Left => left
                                  Shift+Left => left
                                       Right => right
                                 Shift+Right => right
                                          Up => up
                                    Shift+Up => None
                             Ctrl+Alt+Delete => restart
                       Ctrl+Alt+Shift+Delete => restart
                        Ctrl+Alt+Meta+Delete => restart
                                 Ctrl+Delete => None
                  Ctrl+Alt+Meta+Shift+Delete => restart
    '''

    def __init__(self, *pairs):
        super().__init__()
        self._data = collections.defaultdict(set)
        for key, value in pairs:
            self[key] = value

    def find(self, key, default=_raise_exception):
        for candidate, value in self._data[key.keycode]:
            if candidate.matches(key):
                return candidate, value
        else:
            if default is _raise_exception:
                raise KeyError(key)
            else:
                return default

    def __getitem__(self, key):
        _, result = self.find(key)
        return result

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError: pass
        self._data[key.keycode].add((key, value))

    def __delitem__(self, key):
        pair = self.find(key)
        self._data[key.keycode].remove(pair)

    def iteritems(self):
        for keyset in self._data.values():
            yield from keyset

    def __iter__(self):
        for key, _ in self.iteritems():
            yield key

    def __contains__(self, key):
        try:
            self.find(key)
            return True
        except KeyError:
            return False

    def __len__(self):
        i = 0
        for _ in self:
            i += 1
        return i

_key_names = {}
_key_codes = {}

def _k(name, code):
    global _key_names
    _key_names[code] = name
    _key_codes[name] = code

    def fget(self):
        return SimpleKeySequence(self._modifiers, code)

    return property(fget)

class KeySequenceBuilder(object):

    '''
    A class for creating SimpleKeySequence objects. The key codes are the same
    as the ones used in Qt, making translation between Qt key codes and internal
    key codes simple.

    We don't use Qt key sequences directly because we need to support multiple 
    front-ends (e.g. Curses).

    To create a SimpleKeySequence object, use an expression like one of these:
    >>> str(key.esc)
    'Esc'
    >>> str(ctrl.esc)
    'Ctrl+Esc'
    >>> str(ctrl.alt.esc)
    'Ctrl+Alt+Esc'
    '''
    _instances = {}
    def __new__(cls, modifiers):
        self = cls._instances.get(modifiers)
        if self is None:
            self = super().__new__(cls)
            cls._instances[modifiers] = self
        return self

    def __init__(self, modifiers):
        self._modifiers = modifiers


    any                            = _k('any', 0x20)
    space                          = _k('space', 0x20)
    exclam                         = _k('exclam', 0x21)
    quotedbl                       = _k('quotedbl', 0x22)
    numbersign                     = _k('numbersign', 0x23)
    dollar                         = _k('dollar', 0x24)
    percent                        = _k('percent', 0x25)
    ampersand                      = _k('ampersand', 0x26)
    apostrophe                     = _k('apostrophe', 0x27)
    parenleft                      = _k('parenleft', 0x28)
    parenright                     = _k('parenright', 0x29)
    asterisk                       = _k('asterisk', 0x2A)
    plus                           = _k('plus', 0x2B)
    comma                          = _k('comma', 0x2C)
    minus                          = _k('minus', 0x2D)
    period                         = _k('period', 0x2E)
    slash                          = _k('slash', 0x2F)
    zero                           = _k('0', 0x30)
    one                            = _k('1', 0x31)
    two                            = _k('2', 0x32)
    three                          = _k('3', 0x33)
    four                           = _k('4', 0x34)
    five                           = _k('5', 0x35)
    six                            = _k('6', 0x36)
    seven                          = _k('7', 0x37)
    eight                          = _k('8', 0x38)
    nine                           = _k('9', 0x39)
    colon                          = _k('colon', 0x3A)
    semicolon                      = _k('semicolon', 0x3B)
    less                           = _k('less', 0x3C)
    equal                          = _k('equal', 0x3D)
    greater                        = _k('greater', 0x3E)
    question                       = _k('question', 0x3F)
    at                             = _k('at', 0x40)
    a                              = _k('a', 0x41)
    b                              = _k('b', 0x42)
    c                              = _k('c', 0x43)
    d                              = _k('d', 0x44)
    e                              = _k('e', 0x45)
    f                              = _k('f', 0x46)
    g                              = _k('g', 0x47)
    h                              = _k('h', 0x48)
    i                              = _k('i', 0x49)
    j                              = _k('j', 0x4A)
    k                              = _k('k', 0x4B)
    l                              = _k('l', 0x4C)
    m                              = _k('m', 0x4D)
    n                              = _k('n', 0x4E)
    o                              = _k('o', 0x4F)
    p                              = _k('p', 0x50)
    q                              = _k('q', 0x51)
    r                              = _k('r', 0x52)
    s                              = _k('s', 0x53)
    t                              = _k('t', 0x54)
    u                              = _k('u', 0x55)
    v                              = _k('v', 0x56)
    w                              = _k('w', 0x57)
    x                              = _k('x', 0x58)
    y                              = _k('y', 0x59)
    z                              = _k('z', 0x5A)
    bracketleft                    = _k('bracketleft', 0x5B)
    backslash                      = _k('backslash', 0x5C)
    bracketright                   = _k('bracketright', 0x5D)
    asciicircum                    = _k('asciicircum', 0x5E)
    underscore                     = _k('underscore', 0x5F)
    quoteleft                      = _k('quoteleft', 0x60)
    braceleft                      = _k('braceleft', 0x7B)
    bar                            = _k('bar', 0x7C)
    braceright                     = _k('braceright', 0x7D)
    asciitilde                     = _k('asciitilde', 0x7E)
    nobreakspace                   = _k('nobreakspace', 0xA0)
    exclamdown                     = _k('exclamdown', 0xA1)
    cent                           = _k('cent', 0xA2)
    sterling                       = _k('sterling', 0xA3)
    currency                       = _k('currency', 0xA4)
    yen                            = _k('yen', 0xA5)
    brokenbar                      = _k('brokenbar', 0xA6)
    section                        = _k('section', 0xA7)
    diaeresis                      = _k('diaeresis', 0xA8)
    copyright                      = _k('copyright', 0xA9)
    ordfeminine                    = _k('ordfeminine', 0xAA)
    guillemotleft                  = _k('guillemotleft', 0xAB)
    notsign                        = _k('notsign', 0xAC)
    hyphen                         = _k('hyphen', 0xAD)
    registered                     = _k('registered', 0xAE)
    macron                         = _k('macron', 0xAF)
    degree                         = _k('degree', 0xB0)
    plusminus                      = _k('plusminus', 0xB1)
    twosuperior                    = _k('twosuperior', 0xB2)
    threesuperior                  = _k('threesuperior', 0xB3)
    acute                          = _k('acute', 0xB4)
    mu                             = _k('mu', 0xB5)
    paragraph                      = _k('paragraph', 0xB6)
    periodcentered                 = _k('periodcentered', 0xB7)
    cedilla                        = _k('cedilla', 0xB8)
    onesuperior                    = _k('onesuperior', 0xB9)
    masculine                      = _k('masculine', 0xBA)
    guillemotright                 = _k('guillemotright', 0xBB)
    onequarter                     = _k('onequarter', 0xBC)
    onehalf                        = _k('onehalf', 0xBD)
    threequarters                  = _k('threequarters', 0xBE)
    questiondown                   = _k('questiondown', 0xBF)
    agrave                         = _k('agrave', 0xC0)
    aacute                         = _k('aacute', 0xC1)
    acircumflex                    = _k('acircumflex', 0xC2)
    atilde                         = _k('atilde', 0xC3)
    adiaeresis                     = _k('adiaeresis', 0xC4)
    aring                          = _k('aring', 0xC5)
    ae                             = _k('ae', 0xC6)
    ccedilla                       = _k('ccedilla', 0xC7)
    egrave                         = _k('egrave', 0xC8)
    eacute                         = _k('eacute', 0xC9)
    ecircumflex                    = _k('ecircumflex', 0xCA)
    ediaeresis                     = _k('ediaeresis', 0xCB)
    igrave                         = _k('igrave', 0xCC)
    iacute                         = _k('iacute', 0xCD)
    icircumflex                    = _k('icircumflex', 0xCE)
    idiaeresis                     = _k('idiaeresis', 0xCF)
    eth                            = _k('eth', 0xD0)
    ntilde                         = _k('ntilde', 0xD1)
    ograve                         = _k('ograve', 0xD2)
    oacute                         = _k('oacute', 0xD3)
    ocircumflex                    = _k('ocircumflex', 0xD4)
    otilde                         = _k('otilde', 0xD5)
    odiaeresis                     = _k('odiaeresis', 0xD6)
    multiply                       = _k('multiply', 0xD7)
    ooblique                       = _k('ooblique', 0xD8)
    ugrave                         = _k('ugrave', 0xD9)
    uacute                         = _k('uacute', 0xDA)
    ucircumflex                    = _k('ucircumflex', 0xDB)
    udiaeresis                     = _k('udiaeresis', 0xDC)
    yacute                         = _k('yacute', 0xDD)
    thorn                          = _k('thorn', 0xDE)
    ssharp                         = _k('ssharp', 0xDF)
    division                       = _k('division', 0xF7)
    ydiaeresis                     = _k('ydiaeresis', 0xFF)
    escape                         = _k('esc', 0x1000000)
    tab                            = _k('tab', 0x1000001)
    backtab                        = _k('backtab', 0x1000002)
    backspace                      = _k('backspace', 0x1000003)
    return_                        = _k('return', 0x1000004)
    enter                          = _k('enter', 0x1000005)
    insert                         = _k('insert', 0x1000006)
    delete                         = _k('delete', 0x1000007)
    pause                          = _k('pause', 0x1000008)
    printscreen                    = _k('print', 0x1000009)
    sysreq                         = _k('sysreq', 0x100000A)
    clear                          = _k('clear', 0x100000B)
    home                           = _k('home', 0x1000010)
    end                            = _k('end', 0x1000011)
    left                           = _k('left', 0x1000012)
    up                             = _k('up', 0x1000013)
    right                          = _k('right', 0x1000014)
    down                           = _k('down', 0x1000015)
    pageup                         = _k('pageup', 0x1000016)
    pagedown                       = _k('pagedown', 0x1000017)
    #shift                          = _k('shift', 0x1000020)
    #control                        = _k('control', 0x1000021)
    #meta                           = _k('meta', 0x1000022)
    #alt                            = _k('alt', 0x1000023)
    capslock                       = _k('capslock', 0x1000024)
    numlock                        = _k('numlock', 0x1000025)
    scrolllock                     = _k('scrolllock', 0x1000026)
    f1                             = _k('f1', 0x1000030)
    f2                             = _k('f2', 0x1000031)
    f3                             = _k('f3', 0x1000032)
    f4                             = _k('f4', 0x1000033)
    f5                             = _k('f5', 0x1000034)
    f6                             = _k('f6', 0x1000035)
    f7                             = _k('f7', 0x1000036)
    f8                             = _k('f8', 0x1000037)
    f9                             = _k('f9', 0x1000038)
    f10                            = _k('f10', 0x1000039)
    f11                            = _k('f11', 0x100003A)
    f12                            = _k('f12', 0x100003B)
    f13                            = _k('f13', 0x100003C)
    f14                            = _k('f14', 0x100003D)
    f15                            = _k('f15', 0x100003E)
    f16                            = _k('f16', 0x100003F)
    f17                            = _k('f17', 0x1000040)
    f18                            = _k('f18', 0x1000041)
    f19                            = _k('f19', 0x1000042)
    f20                            = _k('f20', 0x1000043)
    f21                            = _k('f21', 0x1000044)
    f22                            = _k('f22', 0x1000045)
    f23                            = _k('f23', 0x1000046)
    f24                            = _k('f24', 0x1000047)
    f25                            = _k('f25', 0x1000048)
    f26                            = _k('f26', 0x1000049)
    f27                            = _k('f27', 0x100004A)
    f28                            = _k('f28', 0x100004B)
    f29                            = _k('f29', 0x100004C)
    f30                            = _k('f30', 0x100004D)
    f31                            = _k('f31', 0x100004E)
    f32                            = _k('f32', 0x100004F)
    f33                            = _k('f33', 0x1000050)
    f34                            = _k('f34', 0x1000051)
    f35                            = _k('f35', 0x1000052)
    super_l                        = _k('super_l', 0x1000053)
    super_r                        = _k('super_r', 0x1000054)
    menu                           = _k('menu', 0x1000055)
    hyper_l                        = _k('hyper_l', 0x1000056)
    hyper_r                        = _k('hyper_r', 0x1000057)
    help                           = _k('help', 0x1000058)
    direction_l                    = _k('direction_l', 0x1000059)
    direction_r                    = _k('direction_r', 0x1000060)
    back                           = _k('back', 0x1000061)
    forward                        = _k('forward', 0x1000062)
    stop                           = _k('stop', 0x1000063)
    refresh                        = _k('refresh', 0x1000064)
    volumedown                     = _k('volumedown', 0x1000070)
    volumemute                     = _k('volumemute', 0x1000071)
    volumeup                       = _k('volumeup', 0x1000072)
    bassboost                      = _k('bassboost', 0x1000073)
    bassup                         = _k('bassup', 0x1000074)
    bassdown                       = _k('bassdown', 0x1000075)
    trebleup                       = _k('trebleup', 0x1000076)
    trebledown                     = _k('trebledown', 0x1000077)
    mediaplay                      = _k('mediaplay', 0x1000080)
    mediastop                      = _k('mediastop', 0x1000081)
    mediaprevious                  = _k('mediaprevious', 0x1000082)
    medianext                      = _k('medianext', 0x1000083)
    mediarecord                    = _k('mediarecord', 0x1000084)
    mediapause                     = _k('mediapause', 0x1000085)
    mediatoggleplaypause           = _k('mediatoggleplaypause', 0x1000086)
    homepage                       = _k('homepage', 0x1000090)
    favorites                      = _k('favorites', 0x1000091)
    search                         = _k('search', 0x1000092)
    standby                        = _k('standby', 0x1000093)
    openurl                        = _k('openurl', 0x1000094)
    launchmail                     = _k('launchmail', 0x10000A0)
    launchmedia                    = _k('launchmedia', 0x10000A1)
    launch0                        = _k('launch0', 0x10000A2)
    launch1                        = _k('launch1', 0x10000A3)
    launch2                        = _k('launch2', 0x10000A4)
    launch3                        = _k('launch3', 0x10000A5)
    launch4                        = _k('launch4', 0x10000A6)
    launch5                        = _k('launch5', 0x10000A7)
    launch6                        = _k('launch6', 0x10000A8)
    launch7                        = _k('launch7', 0x10000A9)
    launch8                        = _k('launch8', 0x10000AA)
    launch9                        = _k('launch9', 0x10000AB)
    launcha                        = _k('launcha', 0x10000AC)
    launchb                        = _k('launchb', 0x10000AD)
    launchc                        = _k('launchc', 0x10000AE)
    launchd                        = _k('launchd', 0x10000AF)
    launche                        = _k('launche', 0x10000B0)
    launchf                        = _k('launchf', 0x10000B1)
    monbrightnessup                = _k('monbrightnessup', 0x10000B2)
    monbrightnessdown              = _k('monbrightnessdown', 0x10000B3)
    keyboardlightonoff             = _k('keyboardlightonoff', 0x10000B4)
    keyboardbrightnessup           = _k('keyboardbrightnessup', 0x10000B5)
    keyboardbrightnessdown         = _k('keyboardbrightnessdown', 0x10000B6)
    poweroff                       = _k('poweroff', 0x10000B7)
    wakeup                         = _k('wakeup', 0x10000B8)
    eject                          = _k('eject', 0x10000B9)
    screensaver                    = _k('screensaver', 0x10000BA)
    www                            = _k('www', 0x10000BB)
    memo                           = _k('memo', 0x10000BC)
    lightbulb                      = _k('lightbulb', 0x10000BD)
    shop                           = _k('shop', 0x10000BE)
    history                        = _k('history', 0x10000BF)
    addfavorite                    = _k('addfavorite', 0x10000C0)
    hotlinks                       = _k('hotlinks', 0x10000C1)
    brightnessadjust               = _k('brightnessadjust', 0x10000C2)
    finance                        = _k('finance', 0x10000C3)
    community                      = _k('community', 0x10000C4)
    audiorewind                    = _k('audiorewind', 0x10000C5)
    backforward                    = _k('backforward', 0x10000C6)
    applicationleft                = _k('applicationleft', 0x10000C7)
    applicationright               = _k('applicationright', 0x10000C8)
    book                           = _k('book', 0x10000C9)
    cd                             = _k('cd', 0x10000CA)
    calculator                     = _k('calculator', 0x10000CB)
    todolist                       = _k('todolist', 0x10000CC)
    cleargrab                      = _k('cleargrab', 0x10000CD)
    close                          = _k('close', 0x10000CE)
    copy                           = _k('copy', 0x10000CF)
    cut                            = _k('cut', 0x10000D0)
    display                        = _k('display', 0x10000D1)
    dos                            = _k('dos', 0x10000D2)
    documents                      = _k('documents', 0x10000D3)
    excel                          = _k('excel', 0x10000D4)
    explorer                       = _k('explorer', 0x10000D5)
    game                           = _k('game', 0x10000D6)
    go                             = _k('go', 0x10000D7)
    itouch                         = _k('itouch', 0x10000D8)
    logoff                         = _k('logoff', 0x10000D9)
    market                         = _k('market', 0x10000DA)
    meeting                        = _k('meeting', 0x10000DB)
    menukb                         = _k('menukb', 0x10000DC)
    menupb                         = _k('menupb', 0x10000DD)
    mysites                        = _k('mysites', 0x10000DE)
    news                           = _k('news', 0x10000DF)
    officehome                     = _k('officehome', 0x10000E0)
    option                         = _k('option', 0x10000E1)
    paste                          = _k('paste', 0x10000E2)
    phone                          = _k('phone', 0x10000E3)
    calendar                       = _k('calendar', 0x10000E4)
    reply                          = _k('reply', 0x10000E5)
    reload                         = _k('reload', 0x10000E6)
    rotatewindows                  = _k('rotatewindows', 0x10000E7)
    rotationpb                     = _k('rotationpb', 0x10000E8)
    rotationkb                     = _k('rotationkb', 0x10000E9)
    save                           = _k('save', 0x10000EA)
    send                           = _k('send', 0x10000EB)
    spell                          = _k('spell', 0x10000EC)
    splitscreen                    = _k('splitscreen', 0x10000ED)
    support                        = _k('support', 0x10000EE)
    taskpane                       = _k('taskpane', 0x10000EF)
    terminal                       = _k('terminal', 0x10000F0)
    tools                          = _k('tools', 0x10000F1)
    travel                         = _k('travel', 0x10000F2)
    video                          = _k('video', 0x10000F3)
    word                           = _k('word', 0x10000F4)
    xfer                           = _k('xfer', 0x10000F5)
    zoomin                         = _k('zoomin', 0x10000F6)
    zoomout                        = _k('zoomout', 0x10000F7)
    away                           = _k('away', 0x10000F8)
    messenger                      = _k('messenger', 0x10000F9)
    webcam                         = _k('webcam', 0x10000FA)
    mailforward                    = _k('mailforward', 0x10000FB)
    pictures                       = _k('pictures', 0x10000FC)
    music                          = _k('music', 0x10000FD)
    battery                        = _k('battery', 0x10000FE)
    bluetooth                      = _k('bluetooth', 0x10000FF)
    wlan                           = _k('wlan', 0x1000100)
    uwb                            = _k('uwb', 0x1000101)
    audioforward                   = _k('audioforward', 0x1000102)
    audiorepeat                    = _k('audiorepeat', 0x1000103)
    audiorandomplay                = _k('audiorandomplay', 0x1000104)
    subtitle                       = _k('subtitle', 0x1000105)
    audiocycletrack                = _k('audiocycletrack', 0x1000106)
    time                           = _k('time', 0x1000107)
    hibernate                      = _k('hibernate', 0x1000108)
    view                           = _k('view', 0x1000109)
    topmenu                        = _k('topmenu', 0x100010A)
    powerdown                      = _k('powerdown', 0x100010B)
    suspend                        = _k('suspend', 0x100010C)
    contrastadjust                 = _k('contrastadjust', 0x100010D)
    launchg                        = _k('launchg', 0x100010E)
    launchh                        = _k('launchh', 0x100010F)
    altgr                          = _k('altgr', 0x1001103)
    multi_key                      = _k('multi_key', 0x1001120)
    kanji                          = _k('kanji', 0x1001121)
    muhenkan                       = _k('muhenkan', 0x1001122)
    henkan                         = _k('henkan', 0x1001123)
    romaji                         = _k('romaji', 0x1001124)
    hiragana                       = _k('hiragana', 0x1001125)
    katakana                       = _k('katakana', 0x1001126)
    hiragana_katakana              = _k('hiragana_katakana', 0x1001127)
    zenkaku                        = _k('zenkaku', 0x1001128)
    hankaku                        = _k('hankaku', 0x1001129)
    zenkaku_hankaku                = _k('zenkaku_hankaku', 0x100112A)
    touroku                        = _k('touroku', 0x100112B)
    massyo                         = _k('massyo', 0x100112C)
    kana_lock                      = _k('kana_lock', 0x100112D)
    kana_shift                     = _k('kana_shift', 0x100112E)
    eisu_shift                     = _k('eisu_shift', 0x100112F)
    eisu_toggle                    = _k('eisu_toggle', 0x1001130)
    hangul                         = _k('hangul', 0x1001131)
    hangul_start                   = _k('hangul_start', 0x1001132)
    hangul_end                     = _k('hangul_end', 0x1001133)
    hangul_hanja                   = _k('hangul_hanja', 0x1001134)
    hangul_jamo                    = _k('hangul_jamo', 0x1001135)
    hangul_romaja                  = _k('hangul_romaja', 0x1001136)
    codeinput                      = _k('codeinput', 0x1001137)
    hangul_jeonja                  = _k('hangul_jeonja', 0x1001138)
    hangul_banja                   = _k('hangul_banja', 0x1001139)
    hangul_prehanja                = _k('hangul_prehanja', 0x100113A)
    hangul_posthanja               = _k('hangul_posthanja', 0x100113B)
    singlecandidate                = _k('singlecandidate', 0x100113C)
    multiplecandidate              = _k('multiplecandidate', 0x100113D)
    previouscandidate              = _k('previouscandidate', 0x100113E)
    hangul_special                 = _k('hangul_special', 0x100113F)
    mode_switch                    = _k('mode_switch', 0x100117E)
    dead_grave                     = _k('dead_grave', 0x1001250)
    dead_acute                     = _k('dead_acute', 0x1001251)
    dead_circumflex                = _k('dead_circumflex', 0x1001252)
    dead_tilde                     = _k('dead_tilde', 0x1001253)
    dead_macron                    = _k('dead_macron', 0x1001254)
    dead_breve                     = _k('dead_breve', 0x1001255)
    dead_abovedot                  = _k('dead_abovedot', 0x1001256)
    dead_diaeresis                 = _k('dead_diaeresis', 0x1001257)
    dead_abovering                 = _k('dead_abovering', 0x1001258)
    dead_doubleacute               = _k('dead_doubleacute', 0x1001259)
    dead_caron                     = _k('dead_caron', 0x100125A)
    dead_cedilla                   = _k('dead_cedilla', 0x100125B)
    dead_ogonek                    = _k('dead_ogonek', 0x100125C)
    dead_iota                      = _k('dead_iota', 0x100125D)
    dead_voiced_sound              = _k('dead_voiced_sound', 0x100125E)
    dead_semivoiced_sound          = _k('dead_semivoiced_sound', 0x100125F)
    dead_belowdot                  = _k('dead_belowdot', 0x1001260)
    dead_hook                      = _k('dead_hook', 0x1001261)
    dead_horn                      = _k('dead_horn', 0x1001262)
    medialast                      = _k('medialast', 0x100FFFF)
    select                         = _k('select', 0x1010000)
    yes                            = _k('yes', 0x1010001)
    no                             = _k('no', 0x1010002)
    cancel                         = _k('cancel', 0x1020001)
    printer                        = _k('printer', 0x1020002)
    execute                        = _k('execute', 0x1020003)
    sleep                          = _k('sleep', 0x1020004)
    play                           = _k('play', 0x1020005)
    zoom                           = _k('zoom', 0x1020006)
    context1                       = _k('context1', 0x1100000)
    context2                       = _k('context2', 0x1100001)
    context3                       = _k('context3', 0x1100002)
    context4                       = _k('context4', 0x1100003)
    call                           = _k('call', 0x1100004)
    hangup                         = _k('hangup', 0x1100005)
    flip                           = _k('flip', 0x1100006)
    togglecallhangup               = _k('togglecallhangup', 0x1100007)
    voicedial                      = _k('voicedial', 0x1100008)
    lastnumberredial               = _k('lastnumberredial', 0x1100009)
    camera                         = _k('camera', 0x1100020)
    camerafocus                    = _k('camerafocus', 0x1100021)
    unknown                        = _k('unknown', 0x1FFFFFF)

    esc = escape

    @classmethod
    def _generate_lines_from_qt(cls):
        from PyQt4.Qt import Qt

        def gen():
            for k,v in vars(Qt).items():
                if k.startswith('Key_'):
                    yield k, int(v)


        for key, value in sorted(gen(), key=lambda x:x[1]):
            if key.startswith('Key_'):
                yield "{0:<30} = _k({0!r}, 0x{1:X})".format(key[4:].lower(), int(value))

    @property
    def shift(self):
        return KeySequenceBuilder(self._modifiers | Modifiers.Shift)

    @property
    def ctrl(self):
        return KeySequenceBuilder(self._modifiers | Modifiers.Ctrl)

    @property
    def alt(self):
        return KeySequenceBuilder(self._modifiers | Modifiers.Alt)

    @property
    def meta(self):
        return KeySequenceBuilder(self._modifiers | Modifiers.Meta)



Keys = KeySequenceBuilder(0)

Ctrl    = Keys.ctrl
Alt     = Keys.alt
Shift   = Keys.shift
Meta    = Keys.meta


