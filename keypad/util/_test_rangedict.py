
import random
import itertools

import pytest

from .rangedict import RangeDict

random.seed(0)
minkey = 0
maxkey = 100

counter = itertools.count()

def random_op():
    k1 = random.randrange(minkey, maxkey)
    k2 = random.randrange(k1, maxkey + 1)

    v = next(counter)

    def delete(d):
        del d[k1:k2]

    def set(d):
        if isinstance(d, list):
            for i in range(k1, k2):
                d[i] = v
        else:
            d[k1:k2] = v

    def get(d):
        try:
            return d[k1]
        except KeyError:
            return None


    def splice(d):
        if hasattr(d, 'splice'):
            d.splice(k1, k2)
        else:
            lo = d[:k1]
            hi = d[k1:]
            v = d[k1-1] if k1 != 0 else None
            d[:] = lo + [v] * k2 + hi

    res = random.choice([delete, set, get, splice])
    res.info = (k1, k2, v)

    return res

def print_op(o):
    print(o.__name__, *o.info)


@pytest.fixture
def random_ops():
    return [random_op() for _ in range(500)]


def fixup(l):
    if len(l) != maxkey + 1:
        l.extend([None] * (maxkey + 1 - len(l)))

def test_ops(random_ops):

    ref = [None] * (maxkey + 1)
    dut = RangeDict()

    for o in random_ops:
        print_op(o)
        r = o(dut)
        s = o(ref)

        fixup(ref)

        dl = list(dut.values(range(len(ref))))
        print(dl)
        print(ref)
        print(dut)
        assert dl == ref
        assert r == s
        print('ok')

