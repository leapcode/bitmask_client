import os

_where = os.path.split(__file__)[0]


def where(filename):
    return os.path.join(_where, filename)
