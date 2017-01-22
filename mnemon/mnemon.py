from collections import MutableMapping
from hashlib import sha256
import pickle
import zlib

from redis import Redis


class MnBackend(MutableMapping):
    _pickle = False
    _expire = None

    def _compress(self, value):
        if self._pickle:
            value = pickle.dumps(value)
        else:
            value = value if type(value) is str else str(value)
            value = value.encode("utf-8")

        return zlib.compress(value)

    def _decompress(self, value):
        value = zlib.decompress(value)

        if self._pickle:
            value = pickle.loads(value)

        return value

    def __init__(self, expire=None, pickle=False):
        self._expire = expire
        self._pickle = pickle

    def __getitem__(self, key):
        pass

    def __setitem__(self, key, value):
        pass

    def __delitem__(self, key):
        pass

    def __iter__(self):
        raise NotImplementedError("No.")

    def __len__(self):
        pass

    def __keytransform__(self, key):
        return sha256(key.encode("utf-8")).hexdigest()


class MnRedis(MnBackend):
    def __init__(self, host="localhost", port=6379, db=0, expire=None,
                 pickle=False):
        super().__init__(expire=expire, pickle=pickle)
        self.d = Redis(host=host, port=port, db=db)

    def __getitem__(self, key):
        return self._decompress(self.d[self.__keytransform__(key)])

    def __setitem__(self, key, value):
        self.d[self.__keytransform__(key)] = self._compress(value)
        if self._expire:
            self.expire(self.__keytransform__(key), self._expire)

    def __delitem__(self, key):
        del self.d[self.__keytransform__(key)]

    def __len__(self):
        # useless
        return len(self.d.keys())

    def expire(self, key, secs=86400):
        self.d.expire(self.__keytransform__(key), secs)


def get_mnemon(backend="redis", **kwargs):
    if backend == "redis":
        return MnRedis(**kwargs)
    else:
        raise NotImplementedError(backend)
