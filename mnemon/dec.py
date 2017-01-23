import json
import hashlib
import functools

from .mnemon import mnemon as mnc


def mnemon(f=None, be="redis", **margs):
    if f is None:
        return functools.partial(mnemon, be=be, **margs)

    def wr(*args, **kwargs):
        with mnc(**margs) as r:
            key = json.dumps({"func": f.__name__, "args": repr(args),
                              "kwargs": repr(kwargs)})
            if be == "redis":
                key = hashlib.sha256(key.encode("utf-8")).hexdigest()

            if key in r:
                return r[key]

            o = f(*args, **kwargs)

            r[key] = o
            if "expire" in margs:
                r.expire(key, margs["expire"])

            return o

    @functools.wraps(f)
    def g(*args, **kwargs):
        return wr(*args, **kwargs)

    return g
