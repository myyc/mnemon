μνήμων
======

A simple cache interface for Python objects. Abuse it.

There are many other caching libraries but this one is very minimal and it's
meant to stay so.

Will add more documentation soon.

Simple usage
------------

```python
from mnemon import mnc

c = mnc()
c[0] = 1
print(c[0])     # returns 1 (obviously)
c.expire(0, 5)  # expires in 5 seconds

del c[0]
```

Can be used in `with`. (`with mnc() as c: ...`). This has no effect on the
`redis` backend.

Decorator usage
---------------

```python
from mnemon import mnd as mn

@mn
def f(x):
    return x
```

Caveats
-------

* Default backend (`be` param to both mnc and mnd) is `redis`. If Redis
  isn't found it will fall back to the `file` backend.
* The `file` backend gets cleaned up every time `mnc()` is called, or on
  `__exit__`.
* Caching by default pickles and compresses (`zlib`) the objects. Initialising
  `mnc` or `mnc` with `raw=True` bypasses pickling but assumes you're caching
  strings or bytes. Good to cache HTTP request results, bad for most other
  cases. Use `raw` only with strings.
* Compression is currently mandatory.
* For now nothing can be configured at runtime besides constructor parameters.
