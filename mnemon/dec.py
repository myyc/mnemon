import json
from functools import wraps

from .mnemon import get_mnemon


def mnemon(f):
    @wraps(f)
    def g(*args, **kwargs):
        mn = get_mnemon()
        force = kwargs.pop("force") if "force" in kwargs else False

        key = json.dumps({"func": f.__name__,
                          "args": repr(args),
                          "kwargs": repr(kwargs)})

        if force and key in mn:
            del mn[key]
        if key in mn:
            return mn[key]

        l = f(*args, **kwargs)

        mn[key] = l

        return l

    return g
