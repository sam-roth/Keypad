

import pytest
import random
import itertools

random.seed(0)
keys = list(range(100))

from .listdict import ListDict


def random_operation():
    k = random.choice(keys)
    v = random.random()

    def delete(d):
        print('deleting', k)
        try:
            del d[k]
        except KeyError:
            return False
        else:
            return True

    def set(d):
        d[k] = v

    def get(d):
        try:
            return d[k]
        except KeyError:
            return None

    return random.choice([delete, set, get])

@pytest.fixture
def random_operations():
    ops = [random_operation() for _ in range(500)]

    return ops


def test_ops(random_operations):
    
    ref = {}
    dut = ListDict()

    for o in random_operations:
        print(o, dut)
        assert sorted(dut.items()) == sorted(ref.items())
        r = o(dut)
        s = o(ref)
        assert r == s








