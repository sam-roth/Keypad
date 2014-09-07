

import pytest
from keypad.util.debug import nonreentrant


@nonreentrant
def _reentrant(limit=5):
    if limit <= 0:
        return

    _reentrant(limit-1)


@nonreentrant
def _nonreentrant1():
    _nonreentrant2()
@nonreentrant
def _nonreentrant2():
    pass

def test_reentrant_fails():
    with pytest.raises(AssertionError):
        _reentrant()
        
def test_nonreentrant_ok():
    _nonreentrant1()




